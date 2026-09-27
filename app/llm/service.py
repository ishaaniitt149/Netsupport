"""LLM orchestration service.

Wraps provider selection, context assembly, and response logging in a single
callable interface.  Domain components should call LLMService, never providers
directly, to keep the abstraction boundary clean.
"""

from __future__ import annotations

import logging

from app.llm.providers import LLMProvider, get_llm_provider
from app.llm.schemas import LLMContext, LLMResponse, LLMTask

logger = logging.getLogger(__name__)


class LLMService:
    """Facade over the LLM provider layer.

    Usage::

        service = LLMService()          # defaults to mock for safety
        response = service.summarise_incident(ctx)
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider: LLMProvider = provider or get_llm_provider("mock")
        logger.info("LLMService initialised with provider: %s", self._provider.model_name)

    # ------------------------------------------------------------------
    # Task convenience methods
    # ------------------------------------------------------------------

    def summarise_incident(self, ctx: LLMContext) -> LLMResponse:
        """Generate an executive incident summary."""
        return self._invoke(ctx, LLMTask.INCIDENT_SUMMARY)

    def explain_rca(self, ctx: LLMContext) -> LLMResponse:
        """Generate an engineer-readable RCA explanation."""
        return self._invoke(ctx, LLMTask.RCA_EXPLANATION)

    def troubleshooting_summary(self, ctx: LLMContext) -> LLMResponse:
        """Generate a step-by-step troubleshooting summary."""
        return self._invoke(ctx, LLMTask.TROUBLESHOOTING_SUMMARY)

    def draft_kb(self, ctx: LLMContext) -> LLMResponse:
        """Generate a KB/SOP draft (always returned as DRAFT, never approved)."""
        return self._invoke(ctx, LLMTask.KB_DRAFT)

    def preventive_actions(self, ctx: LLMContext) -> LLMResponse:
        """Generate preventive action recommendations."""
        return self._invoke(ctx, LLMTask.PREVENTIVE_ACTION)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _invoke(self, ctx: LLMContext, task: LLMTask) -> LLMResponse:
        # Override the task on the context so prompt builder picks the right template
        ctx_with_task = ctx.model_copy(update={"task": task})
        logger.debug(
            "LLM invoke | task=%s | incident=%s | provider=%s",
            task, ctx.incident_id, self._provider.model_name,
        )
        try:
            response = self._provider.complete(ctx_with_task)
            logger.debug("LLM response | latency=%.1fms | tokens=%d", response.latency_ms, response.completion_tokens)
            return response
        except Exception as exc:
            logger.error("LLM provider error: %s", exc, exc_info=True)
            raise
