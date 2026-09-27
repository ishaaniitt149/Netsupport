"""Comprehensive tests for the LLM abstraction layer.

All tests use MockLLMProvider — no API key or network call is required.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.llm.prompts import build_prompt
from app.llm.providers import MockLLMProvider, OpenAICompatibleProvider, get_llm_provider
from app.llm.schemas import LLMContext, LLMResponse, LLMTask
from app.llm.service import LLMService

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def base_ctx() -> LLMContext:
    return LLMContext(
        task=LLMTask.INCIDENT_SUMMARY,
        incident_id="INC-0001",
        device_id="DEV-CSCO-0001",
        alert_type="NODE_DOWN",
        severity="critical",
        start_time=datetime(2023, 6, 1, 10, 0, tzinfo=UTC),
        recovery_time=datetime(2023, 6, 1, 10, 22, tzinfo=UTC),
        duration_minutes=22.0,
        probable_rca="Interface degradation",
        rca_confidence=0.88,
        rca_rule_id="RULE-001-INTERFACE-DEGRADATION",
        rca_evidence={"crc_errors": "1450", "interface_flaps": "8", "bgp_status": "ESTABLISHED"},
        rca_recommended_checks=["Clean fiber optics", "Replace SFP module"],
        cpu_utilization=42.0,
        memory_utilization=51.0,
        crc_errors=1450,
        interface_flaps=8,
        bgp_status="ESTABLISHED",
        root_cause="Faulty SFP transceiver on Gi0/1",
        resolution_action="Replaced SFP module on Gi0/1",
        validation_action="Confirmed zero CRC errors over 15 min",
        resolved_by="Alice Smith",
        resolution_duration_minutes=45.0,
        first_time_resolution=True,
    )


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def llm_service() -> LLMService:
    return LLMService()  # defaults to mock


# ---------------------------------------------------------------------------
# MockLLMProvider: all five tasks
# ---------------------------------------------------------------------------

class TestMockLLMProvider:
    def test_incident_summary_returns_response(self, mock_provider, base_ctx):
        ctx = base_ctx.model_copy(update={"task": LLMTask.INCIDENT_SUMMARY})
        resp = mock_provider.complete(ctx)
        assert isinstance(resp, LLMResponse)
        assert resp.task == LLMTask.INCIDENT_SUMMARY
        assert resp.incident_id == "INC-0001"
        assert resp.grounded is True
        assert resp.model_used == "mock-llm-v1"

    def test_incident_summary_contains_key_facts(self, mock_provider, base_ctx):
        ctx = base_ctx.model_copy(update={"task": LLMTask.INCIDENT_SUMMARY})
        resp = mock_provider.complete(ctx)
        assert "INC-0001" in resp.content
        assert "DEV-CSCO-0001" in resp.content
        assert "Interface degradation" in resp.content
        assert "crc_errors=1450" in resp.content

    def test_rca_explanation_references_rule_id(self, mock_provider, base_ctx):
        ctx = base_ctx.model_copy(update={"task": LLMTask.RCA_EXPLANATION})
        resp = mock_provider.complete(ctx)
        assert "RULE-001-INTERFACE-DEGRADATION" in resp.content
        assert "88%" in resp.content  # confidence

    def test_troubleshooting_summary_structure(self, mock_provider, base_ctx):
        ctx = base_ctx.model_copy(update={"task": LLMTask.TROUBLESHOOTING_SUMMARY})
        resp = mock_provider.complete(ctx)
        assert "SYMPTOMS OBSERVED" in resp.content
        assert "PROBABLE CAUSE" in resp.content
        assert "RECOMMENDED CHECKS" in resp.content
        assert "RESOLUTION" in resp.content

    def test_kb_draft_marked_as_draft(self, mock_provider, base_ctx):
        ctx = base_ctx.model_copy(update={"task": LLMTask.KB_DRAFT})
        resp = mock_provider.complete(ctx)
        assert "DRAFT" in resp.content
        assert "NOT APPROVED" in resp.content
        assert "PROBLEM STATEMENT" in resp.content
        assert "ROOT CAUSE" in resp.content
        assert "EVIDENCE" in resp.content

    def test_preventive_actions_uses_recommended_checks(self, mock_provider, base_ctx):
        ctx = base_ctx.model_copy(update={"task": LLMTask.PREVENTIVE_ACTION})
        resp = mock_provider.complete(ctx)
        assert "Clean fiber optics" in resp.content
        assert "Replace SFP module" in resp.content

    def test_mock_disclaimer_present_in_all_tasks(self, mock_provider, base_ctx):
        for task in LLMTask:
            ctx = base_ctx.model_copy(update={"task": task})
            resp = mock_provider.complete(ctx)
            assert "MOCK PROVIDER" in resp.content, f"Disclaimer missing for task {task}"


# ---------------------------------------------------------------------------
# Mock handles missing optional fields gracefully
# ---------------------------------------------------------------------------

class TestMockLLMProviderMissingFields:
    @pytest.fixture
    def minimal_ctx(self) -> LLMContext:
        return LLMContext(
            task=LLMTask.INCIDENT_SUMMARY,
            incident_id="INC-9999",
            device_id="DEV-X",
            alert_type="PACKET_LOSS",
            severity="warning",
            start_time=datetime(2023, 1, 1, tzinfo=UTC),
            probable_rca="WAN degradation",
            rca_confidence=0.75,
            rca_rule_id="RULE-005-WAN-DEGRADATION",
            rca_evidence={"packet_loss": "15%"},
            rca_recommended_checks=[],
        )

    def test_no_recovery_shows_not_recovered(self, mock_provider, minimal_ctx):
        resp = mock_provider.complete(minimal_ctx)
        assert "not yet recovered" in resp.content

    def test_no_resolution_shows_not_available(self, mock_provider, minimal_ctx):
        ctx = minimal_ctx.model_copy(update={"task": LLMTask.TROUBLESHOOTING_SUMMARY})
        resp = mock_provider.complete(ctx)
        assert "Not available" in resp.content

    def test_empty_recommended_checks(self, mock_provider, minimal_ctx):
        ctx = minimal_ctx.model_copy(update={"task": LLMTask.PREVENTIVE_ACTION})
        resp = mock_provider.complete(ctx)
        # Should not crash; should state no checks available
        assert resp.content is not None


# ---------------------------------------------------------------------------
# Prompt builder: grounding contract is always present
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def test_grounding_contract_in_system_prompt(self, base_ctx):
        for task in LLMTask:
            ctx = base_ctx.model_copy(update={"task": task})
            system, user = build_prompt(ctx)
            assert "GROUNDING CONTRACT" in system, f"Missing grounding contract in task {task}"
            assert "do NOT invent" in system.lower() or "do not invent" in system.lower()

    def test_evidence_echoed_verbatim_in_user_prompt(self, base_ctx):
        ctx = base_ctx.model_copy(update={"task": LLMTask.RCA_EXPLANATION})
        _, user = build_prompt(ctx)
        assert "crc_errors: 1450" in user
        assert "interface_flaps: 8" in user

    def test_not_available_label_for_missing_fields(self, base_ctx):
        ctx = base_ctx.model_copy(update={
            "task": LLMTask.INCIDENT_SUMMARY,
            "cpu_utilization": None,
            "bgp_status": None,
        })
        _, user = build_prompt(ctx)
        assert "Not available" in user

    def test_resolution_block_appears_when_present(self, base_ctx):
        ctx = base_ctx.model_copy(update={"task": LLMTask.KB_DRAFT})
        _, user = build_prompt(ctx)
        assert "Faulty SFP transceiver on Gi0/1" in user
        assert "Alice Smith" in user


# ---------------------------------------------------------------------------
# LLMService facade
# ---------------------------------------------------------------------------

class TestLLMService:
    def test_defaults_to_mock_provider(self, llm_service):
        assert llm_service._provider.model_name == "mock-llm-v1"

    def test_summarise_incident(self, llm_service, base_ctx):
        resp = llm_service.summarise_incident(base_ctx)
        assert resp.task == LLMTask.INCIDENT_SUMMARY

    def test_explain_rca(self, llm_service, base_ctx):
        resp = llm_service.explain_rca(base_ctx)
        assert resp.task == LLMTask.RCA_EXPLANATION

    def test_troubleshooting_summary(self, llm_service, base_ctx):
        resp = llm_service.troubleshooting_summary(base_ctx)
        assert resp.task == LLMTask.TROUBLESHOOTING_SUMMARY

    def test_draft_kb(self, llm_service, base_ctx):
        resp = llm_service.draft_kb(base_ctx)
        assert resp.task == LLMTask.KB_DRAFT

    def test_preventive_actions(self, llm_service, base_ctx):
        resp = llm_service.preventive_actions(base_ctx)
        assert resp.task == LLMTask.PREVENTIVE_ACTION

    def test_accepts_custom_provider(self, base_ctx):
        custom = MockLLMProvider()
        service = LLMService(provider=custom)
        resp = service.summarise_incident(base_ctx)
        assert "INC-0001" in resp.content


# ---------------------------------------------------------------------------
# OpenAI provider: refuses to initialise without API key
# ---------------------------------------------------------------------------

class TestOpenAIProviderSecurity:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="No API key found"):
            OpenAICompatibleProvider()

    def test_no_api_key_in_source_code(self):
        """Ensure no hard-coded key patterns appear in providers.py."""
        import inspect

        from app.llm import providers
        source = inspect.getsource(providers)
        # A real key would look like sk-... (OpenAI) or a long alphanumeric string
        # We just check that the word 'sk-' isn't hard-coded as a string literal
        assert 'api_key = "sk-' not in source
        assert "api_key = 'sk-" not in source


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestGetLLMProvider:
    def test_mock_factory(self):
        p = get_llm_provider("mock")
        assert isinstance(p, MockLLMProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_llm_provider("unknown-provider")

    def test_openai_factory_raises_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        with pytest.raises(EnvironmentError):
            get_llm_provider("openai")
