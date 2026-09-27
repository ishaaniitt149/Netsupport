"""LLM provider abstraction: Protocol, OpenAI-compatible adapter, and Mock.

The application ALWAYS works without an API key by falling back to
MockLLMProvider. No API key is ever stored in source code.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod

from app.llm.prompts import build_prompt
from app.llm.schemas import LLMContext, LLMResponse, LLMTask

# ---------------------------------------------------------------------------
# Abstract base (interface contract)
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract base class for all LLM provider adapters.

    Implementations must:
      - Accept a fully-populated LLMContext (never raw strings).
      - Invoke build_prompt() to obtain grounding-contract-prefixed prompts.
      - Return a structured LLMResponse.
    """

    @abstractmethod
    def complete(self, ctx: LLMContext) -> LLMResponse:
        """Send a grounded prompt to the underlying model and return output."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable identifier of the backing model."""
        ...


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (works with OpenAI, Azure OpenAI, local llama.cpp
# servers, or any endpoint that follows the /v1/chat/completions contract)
# ---------------------------------------------------------------------------

class OpenAICompatibleProvider(LLMProvider):
    """OpenAI /v1/chat/completions adapter.

    API key is loaded exclusively from the environment variable
    ``OPENAI_API_KEY`` (or ``LLM_API_KEY``).  It is NEVER accepted as a
    constructor parameter to prevent accidental leakage into source code or
    logs.

    Args:
        model: Model identifier, e.g. ``"gpt-4o-mini"``.
        base_url: Base URL for the API endpoint.
        temperature: Sampling temperature (0.0 for deterministic output).
        timeout: Request timeout in seconds.
        max_tokens: Maximum tokens in the completion.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.0,
        timeout: int = 30,
        max_tokens: int = 1024,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._timeout = timeout
        self._max_tokens = max_tokens

        # Key loaded from environment — never from code
        self._api_key: str | None = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
        if not self._api_key:
            raise OSError(
                "No API key found. Set the OPENAI_API_KEY or LLM_API_KEY environment variable. "
                "Use MockLLMProvider for keyless operation."
            )

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, ctx: LLMContext) -> LLMResponse:
        import httpx  # Lazy import — keeps startup fast when using Mock

        system_prompt, user_prompt = build_prompt(ctx)
        payload = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        t0 = time.monotonic()
        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        latency_ms = (time.monotonic() - t0) * 1000

        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            task=ctx.task,
            incident_id=ctx.incident_id,
            content=content,
            model_used=self._model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=round(latency_ms, 2),
            grounded=True,
        )


# ---------------------------------------------------------------------------
# Mock provider — zero network calls, zero API key required
# ---------------------------------------------------------------------------

class MockLLMProvider(LLMProvider):
    """Deterministic mock provider for local development and CI testing.

    Generates templated responses that:
      - Reference the actual incident_id and device_id from the context.
      - Echo observed evidence verbatim rather than inventing values.
      - Include the grounding contract disclaimer so tests can assert it.

    Suitable for all environments that lack an API key.
    """

    _DISCLAIMER = (
        "[MOCK PROVIDER — No LLM API call was made. "
        "In production, configure OPENAI_API_KEY to use a real model.]"
    )

    @property
    def model_name(self) -> str:
        return "mock-llm-v1"

    def complete(self, ctx: LLMContext) -> LLMResponse:
        content = self._generate(ctx)
        return LLMResponse(
            task=ctx.task,
            incident_id=ctx.incident_id,
            content=content,
            model_used=self.model_name,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0.0,
            grounded=True,
        )

    def _generate(self, ctx: LLMContext) -> str:
        evidence_str = "; ".join(f"{k}={v}" for k, v in ctx.rca_evidence.items()) or "(none)"
        recovery_str = (
            f"recovered at {ctx.recovery_time.isoformat()}, duration {ctx.duration_minutes:.1f} min"
            if ctx.recovery_time
            else "not yet recovered"
        )

        if ctx.task == LLMTask.INCIDENT_SUMMARY:
            return (
                f"{self._DISCLAIMER}\n\n"
                f"INCIDENT SUMMARY — {ctx.incident_id}\n"
                f"Device {ctx.device_id} raised a {ctx.alert_type} ({ctx.severity}) alert "
                f"at {ctx.start_time.isoformat()}; {recovery_str}.\n\n"
                f"Diagnostics showed: {evidence_str}.\n"
                f"The RCA engine ({ctx.rca_rule_id}, confidence {ctx.rca_confidence:.0%}) "
                f"identified probable cause: {ctx.probable_rca}.\n\n"
                f"Recommended next steps: {'; '.join(ctx.rca_recommended_checks) or 'See rule engine output'}."
            )

        elif ctx.task == LLMTask.RCA_EXPLANATION:
            return (
                f"{self._DISCLAIMER}\n\n"
                f"RCA EXPLANATION — {ctx.incident_id}\n"
                f"Rule {ctx.rca_rule_id} fired with {ctx.rca_confidence:.0%} confidence.\n"
                f"Observed evidence: {evidence_str}.\n"
                f"Probable root cause: {ctx.probable_rca}.\n"
                f"CPU: {ctx.cpu_utilization if ctx.cpu_utilization is not None else 'Not available'}% | "
                f"Memory: {ctx.memory_utilization if ctx.memory_utilization is not None else 'Not available'}% | "
                f"BGP: {ctx.bgp_status or 'Not available'} | "
                f"OSPF: {ctx.ospf_status or 'Not available'}."
            )

        elif ctx.task == LLMTask.TROUBLESHOOTING_SUMMARY:
            checks = "\n  ".join(f"- {c}" for c in ctx.rca_recommended_checks) or "  - See rule engine output"
            return (
                f"{self._DISCLAIMER}\n\n"
                f"TROUBLESHOOTING SUMMARY — {ctx.incident_id}\n\n"
                f"SYMPTOMS OBSERVED:\n  {evidence_str}\n\n"
                f"PROBABLE CAUSE: {ctx.probable_rca} (rule {ctx.rca_rule_id})\n\n"
                f"RECOMMENDED CHECKS:\n  {checks}\n\n"
                f"RESOLUTION: {ctx.resolution_action or 'Not available'}"
            )

        elif ctx.task == LLMTask.KB_DRAFT:
            return (
                f"{self._DISCLAIMER}\n\n"
                f"[DRAFT — NOT APPROVED]\n\n"
                f"PROBLEM STATEMENT\n"
                f"Device {ctx.device_id} experienced {ctx.probable_rca}.\n\n"
                f"SYMPTOMS\n{evidence_str}\n\n"
                f"ROOT CAUSE\n{ctx.probable_rca} (confidence {ctx.rca_confidence:.0%})\n\n"
                f"EVIDENCE\n{evidence_str}\n\n"
                f"RESOLUTION STEPS\n{ctx.resolution_action or '(see recommended checks)'}\n\n"
                f"VALIDATION STEPS\n{ctx.validation_action or 'Not available'}\n\n"
                f"ROLLBACK STEPS\n(consult engineering team)\n\n"
                f"NOTES\nThis draft was generated from observed evidence only. "
                f"It must be reviewed and approved before use."
            )

        elif ctx.task == LLMTask.PREVENTIVE_ACTION:
            checks = "\n".join(
                f"{i + 1}. {c}" for i, c in enumerate(ctx.rca_recommended_checks)
            ) or "1. No specific preventive actions available from context."
            return (
                f"{self._DISCLAIMER}\n\n"
                f"PREVENTIVE ACTIONS — {ctx.incident_id}\n"
                f"Based on rule {ctx.rca_rule_id} ({ctx.probable_rca}):\n\n"
                f"{checks}"
            )

        return f"{self._DISCLAIMER}\n\n[Unknown task: {ctx.task}]"


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def get_llm_provider(provider_name: str = "mock") -> LLMProvider:
    """Return the appropriate LLM provider.

    Precedence:
      1. ``"mock"`` → MockLLMProvider (always available, no key needed).
      2. ``"openai"`` → OpenAICompatibleProvider (requires OPENAI_API_KEY env var).

    Args:
        provider_name: One of ``"mock"`` or ``"openai"``.
    """
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name == "openai":
        return OpenAICompatibleProvider()
    raise ValueError(f"Unknown provider: '{provider_name}'. Supported: 'mock', 'openai'.")
