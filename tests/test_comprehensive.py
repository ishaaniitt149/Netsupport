"""
Comprehensive test suite for NOIPMP.

Covers:
- Unit tests (models, schemas)
- Integration tests (pipeline end-to-end)
- Data validation tests
- ML pipeline tests (including model_unavailable)
- API tests
- RCA parser tests (malformed / missing)
- Correlation tests (missing_alert, duplicate_alert, missing_recovery)
- KB versioning tests (immutability, FSM)
- Vulnerability matching tests (invalid_cve, unknown_device, invalid_firmware)
- LLM layer tests (llm_unavailable, mock fallback)

Failure conditions tested:
  missing_alert, missing_rca, duplicate_alert, malformed_rca,
  unknown_device, invalid_firmware, missing_telemetry, llm_unavailable,
  invalid_cve, model_unavailable
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

# =========================================================================== #
# 1. UNIT TESTS – Models & Schemas                                             #
# =========================================================================== #


class TestDeviceModel:
    def _base_kwargs(self, **overrides):
        base = dict(
            device_id="DEV-001",
            hostname="rtr-001.example.com",
            vendor="Cisco",
            model="ISR-4451",
            serial_number="ABC1234567XY",
            firmware_version="16.9.6",
            location="DC-West",
            region="us-west-2",
            device_type="router",
            criticality="HIGH",
            interface_count=8,
            last_patch_date=date(2023, 1, 1),
            customer="Acme-01",
            network_segment="10.0.0.0/24",
        )
        base.update(overrides)
        return base

    def test_valid_device_record(self):
        from app.models.device import DeviceRecord

        dev = DeviceRecord(**self._base_kwargs())
        assert dev.vendor == "Cisco"
        assert dev.interface_count == 8

    def test_invalid_vendor_rejected(self):
        from pydantic import ValidationError

        from app.models.device import DeviceRecord

        with pytest.raises(ValidationError, match="Vendor must be Cisco"):
            DeviceRecord(**self._base_kwargs(vendor="Juniper"))

    def test_interface_count_upper_bound(self):
        from pydantic import ValidationError

        from app.models.device import DeviceRecord

        with pytest.raises(ValidationError):
            DeviceRecord(**self._base_kwargs(interface_count=200))

    def test_interface_count_lower_bound(self):
        from pydantic import ValidationError

        from app.models.device import DeviceRecord

        with pytest.raises(ValidationError):
            DeviceRecord(**self._base_kwargs(interface_count=0))


class TestIncidentModel:
    """Unit tests for the canonical Incident model."""

    def test_incident_optional_recovery(self):
        from app.core.constants import IncidentState
        from app.models.incident import Incident

        inc = Incident(
            incident_id="INC-001",
            device_id="DEV-001",
            device_hostname="rtr001.corp",
            device_ip="10.0.0.1",
        )
        assert inc.recovery_timestamp is None
        assert inc.outage_duration_sec is None
        assert inc.state == IncidentState.ALERT_RECEIVED

    def test_incident_severity_default(self):
        from app.core.constants import Severity
        from app.models.incident import Incident

        inc = Incident(
            incident_id="INC-002",
            device_id="DEV-002",
            device_hostname="rtr002.corp",
            device_ip="10.0.0.2",
        )
        assert inc.severity == Severity.CRITICAL


# =========================================================================== #
# 2. RCA PARSER TESTS                                                          #
# =========================================================================== #


class TestRCAParser:
    def _parser(self):
        from app.rca.parser import CiscoRCAParser
        return CiscoRCAParser()

    def test_full_output(self):
        parser = self._parser()
        raw = """
        >> show interfaces Gi0/1
        Interface is UP
        CRC errors: 1450
        Input errors: 1510
        Output errors: 23
        Interface flaps: 8

        >> show processes cpu
        CPU utilization: 42.5%

        >> show memory
        Memory utilization: 51%

        >> show ip bgp summary
        10.0.0.2 4 65001 1434 1435 142 0 0 23:14:02 1

        >> show ip ospf neighbor
        192.168.1.2 1 FULL/BDR 00:00:32 10.1.1.2 GigabitEthernet0/1

        >> show logging
        Syslog logging: enabled
        """
        parsed = parser.parse("INC-100_rca.txt", raw)
        assert parsed.cpu_utilization == 42.5
        assert parsed.crc_errors == 1450
        assert parsed.bgp_status == "ESTABLISHED"
        assert parsed.ospf_status == "FULL"

    def test_malformed_rca_empty_text(self):
        """FAILURE CONDITION: malformed_rca – empty text → all fields None, no crash."""
        parser = self._parser()
        parsed = parser.parse("malformed.txt", "")
        assert parsed.cpu_utilization is None
        assert parsed.memory_utilization is None
        assert parsed.crc_errors is None
        assert parsed.interface_status is None
        assert parsed.bgp_status is None

    def test_malformed_rca_garbage_text(self):
        """FAILURE CONDITION: malformed_rca – garbage → parser must not crash."""
        parser = self._parser()
        garbage = "!@#$%^&*() gibberish 0xDEADBEEF 中文 emoji 🔥"
        parsed = parser.parse("garbage.txt", garbage)
        assert parsed is not None

    def test_missing_cpu_field(self):
        """FAILURE CONDITION: partial RCA – missing cpu field parsed safely."""
        parser = self._parser()
        raw = ">> show memory\nMemory utilization: 60%\n"
        parsed = parser.parse("no_cpu.txt", raw)
        assert parsed.cpu_utilization is None
        assert parsed.memory_utilization == 60.0

    def test_missing_interface_output(self):
        parser = self._parser()
        raw = ">> show processes cpu\nCPU utilization: 30%\n"
        parsed = parser.parse("no_iface.txt", raw)
        assert parsed.crc_errors is None
        assert parsed.interface_flaps is None
        assert parsed.interface_status is None

    def test_bgp_idle_state(self):
        parser = self._parser()
        raw = """
        >> show ip bgp summary
        10.0.0.2 4 65001 0 0 0 0 0 never Idle
        """
        parsed = parser.parse("bgp_idle.txt", raw)
        assert parsed.bgp_status == "IDLE"

    def test_raw_command_output_preserved(self):
        parser = self._parser()
        raw = ">> show processes cpu\nCPU utilization: 55%\n"
        parsed = parser.parse("preserve.txt", raw)
        assert raw in parsed.raw_command_output


# =========================================================================== #
# 3. CORRELATION ENGINE TESTS                                                  #
# =========================================================================== #


class TestCorrelationEngine:
    def _make_events_csv(self, path: Path, rows: list[str]) -> None:
        path.write_text(
            "event_id,device_id,event_type,severity,timestamp\n" + "\n".join(rows),
            encoding="utf-8",
        )

    def _make_rca_csv(self, path: Path, rows: list[str] = None) -> None:
        content = "incident_id,device_id,rca_file,alert_event_id,recovery_event_id\n"
        if rows:
            content += "\n".join(rows)
        path.write_text(content, encoding="utf-8")

    def _engine(self, tmp_path, event_rows, rca_rows=None):
        from app.correlation.engine import CorrelationEngine

        ev = tmp_path / "events.csv"
        rca = tmp_path / "rca_meta.csv"
        out = tmp_path / "incidents.parquet"
        self._make_events_csv(ev, event_rows)
        self._make_rca_csv(rca, rca_rows or [])
        return CorrelationEngine(ev, rca, out), out

    def test_basic_correlation_creates_incident(self, tmp_path):
        engine, out = self._engine(tmp_path, [
            "E1,DEV-001,NODE_DOWN,critical,2023-01-01T10:00:00Z",
            "E2,DEV-001,NODE_UP,info,2023-01-01T10:20:00Z",
        ])
        incidents = engine.run()
        assert any(i.device_id == "DEV-001" for i in incidents)
        assert out.exists()

    def test_duration_calculated_correctly(self, tmp_path):
        engine, _ = self._engine(tmp_path, [
            "E1,DEV-001,NODE_DOWN,critical,2023-01-01T10:00:00Z",
            "E2,DEV-001,NODE_UP,info,2023-01-01T10:20:00Z",
        ])
        incidents = engine.run()
        inc = next(i for i in incidents if i.device_id == "DEV-001")
        assert inc.duration_minutes == pytest.approx(20.0, abs=1.0)

    def test_missing_recovery_event(self, tmp_path):
        """FAILURE CONDITION: missing_recovery – incident created with no duration."""
        engine, _ = self._engine(tmp_path, [
            "E1,DEV-001,NODE_DOWN,critical,2023-01-01T10:00:00Z",
        ])
        incidents = engine.run()
        assert len(incidents) == 1
        assert incidents[0].recovery_time is None
        assert incidents[0].duration_minutes is None

    def test_missing_alert_only_recovery(self, tmp_path):
        """FAILURE CONDITION: missing_alert – stray recovery event, no incident created."""
        engine, _ = self._engine(tmp_path, [
            "E1,DEV-001,NODE_UP,info,2023-01-01T10:20:00Z",
        ])
        incidents = engine.run()
        assert all(i.device_id != "DEV-001" for i in incidents)

    def test_duplicate_alert_deduplication(self, tmp_path):
        """FAILURE CONDITION: duplicate_alert – two near-identical NODE_DOWN → one incident."""
        engine, _ = self._engine(tmp_path, [
            "E1,DEV-001,NODE_DOWN,critical,2023-01-01T10:00:00Z",
            "E2,DEV-001,NODE_DOWN,critical,2023-01-01T10:00:05Z",
            "E3,DEV-001,NODE_UP,info,2023-01-01T10:20:00Z",
        ])
        incidents = engine.run()
        dev_incidents = [i for i in incidents if i.device_id == "DEV-001"]
        assert len(dev_incidents) == 1

    def test_missing_rca_reference(self, tmp_path):
        """FAILURE CONDITION: missing_rca – RCA file referenced but missing → no crash."""
        engine, _ = self._engine(tmp_path, [
            "E1,DEV-001,NODE_DOWN,critical,2023-01-01T10:00:00Z",
            "E2,DEV-001,NODE_UP,info,2023-01-01T10:20:00Z",
        ], rca_rows=["INC-999,DEV-001,missing_rca.txt,E1,E2"])
        incidents = engine.run()
        assert len(incidents) >= 1

    def test_unknown_device_handled(self, tmp_path):
        """FAILURE CONDITION: unknown_device in events → correlates without crash."""
        engine, _ = self._engine(tmp_path, [
            "E1,UNKNOWN-XYZ,NODE_DOWN,critical,2023-01-01T10:00:00Z",
            "E2,UNKNOWN-XYZ,NODE_UP,info,2023-01-01T10:10:00Z",
        ])
        incidents = engine.run()
        assert any(i.device_id == "UNKNOWN-XYZ" for i in incidents)

    def test_parquet_output_written(self, tmp_path):
        engine, out = self._engine(tmp_path, [
            "E1,DEV-001,NODE_DOWN,critical,2023-01-01T10:00:00Z",
            "E2,DEV-001,NODE_UP,info,2023-01-01T10:20:00Z",
        ])
        engine.run()
        assert out.exists()
        df = pd.read_parquet(out)
        assert len(df) >= 1


# =========================================================================== #
# 4. DATA VALIDATION TESTS                                                     #
# =========================================================================== #


class TestDataValidation:
    def test_device_generator_output_count(self):
        from scripts.generate_devices import generate_devices

        devices = generate_devices(number_of_devices=10, random_seed=99)
        assert len(devices) == 10

    def test_device_generator_unique_ids(self):
        from scripts.generate_devices import generate_devices

        devices = generate_devices(number_of_devices=20, random_seed=7)
        ids = [d.device_id for d in devices]
        assert len(ids) == len(set(ids))

    def test_missing_telemetry_handled_in_feature_pipeline(self):
        """FAILURE CONDITION: missing_telemetry → feature pipeline returns empty, no crash."""
        from app.predictive.feature_pipeline import FeaturePipeline

        pipeline = FeaturePipeline(
            telemetry_df=pd.DataFrame(),
            incidents_df=pd.DataFrame(),
            device_meta_df=pd.DataFrame(),
        )
        result = pipeline.create_features()
        assert result.empty


# =========================================================================== #
# 5. ML PIPELINE TESTS                                                         #
# =========================================================================== #


class TestMLPipeline:
    def _dataset(self, n=80):
        base = datetime(2023, 1, 1)
        rows = []
        for i in range(n):
            rows.append({
                "timestamp": base + timedelta(hours=i),
                "device_id": "DEV-001",
                "f1": 10.0 if i % 5 == 0 else 0.1,
                "f2": 50.0 if i % 5 == 0 else 0.5,
                "incident_next_7_days": 1 if i % 5 == 0 else 0,
            })
        return pd.DataFrame(rows)

    def test_train_and_evaluate_returns_all_metrics(self, tmp_path):
        from app.predictive.ml_pipeline import MLPipeline

        pipeline = MLPipeline(artifact_dir=tmp_path)
        metrics = pipeline.train_and_evaluate(self._dataset(), ["f1", "f2"], "incident_next_7_days")

        for key in ["precision", "recall", "f1", "roc_auc", "pr_auc",
                    "false_positives", "false_negatives", "feature_importance"]:
            assert key in metrics, f"Missing metric: {key}"

    def test_artifacts_saved_after_training(self, tmp_path):
        from app.predictive.ml_pipeline import MLPipeline

        pipeline = MLPipeline(artifact_dir=tmp_path)
        pipeline.train_and_evaluate(self._dataset(), ["f1", "f2"], "incident_next_7_days")

        assert (tmp_path / "rf_model.joblib").exists()
        assert (tmp_path / "metrics.json").exists()
        assert (tmp_path / "features.json").exists()

    def test_model_unavailable_raises_value_error(self, tmp_path):
        """FAILURE CONDITION: model_unavailable → predict raises ValueError."""
        from app.predictive.ml_pipeline import MLPipeline

        pipeline = MLPipeline(artifact_dir=tmp_path)
        pipeline.features = ["f1", "f2"]   # set features but no model object

        df = pd.DataFrame([{
            "timestamp": datetime(2023, 1, 1),
            "device_id": "DEV-001",
            "f1": 1.0,
            "f2": 2.0,
        }])
        with pytest.raises(ValueError, match="Model not trained"):
            pipeline.predict(df)

    def test_time_aware_split_preserves_order(self, tmp_path):
        from app.predictive.ml_pipeline import MLPipeline

        pipeline = MLPipeline(artifact_dir=tmp_path)
        df = self._dataset(100)
        train, test = pipeline.time_aware_split(df, "incident_next_7_days")
        assert train["timestamp"].max() < test["timestamp"].min()

    def test_risk_level_thresholds(self, tmp_path):
        from app.predictive.ml_pipeline import MLPipeline, RiskLevel

        pipeline = MLPipeline(artifact_dir=tmp_path)
        assert pipeline._determine_risk_level(0.10) == RiskLevel.LOW
        assert pipeline._determine_risk_level(0.30) == RiskLevel.MEDIUM
        assert pipeline._determine_risk_level(0.60) == RiskLevel.HIGH
        assert pipeline._determine_risk_level(0.90) == RiskLevel.CRITICAL


# =========================================================================== #
# 6. API TESTS                                                                 #
# =========================================================================== #


class TestAPIEndpoints:
    def _client(self):
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app)

    def test_health_endpoint_returns_ok(self):
        response = self._client().get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"

    def test_health_includes_version(self):
        response = self._client().get("/api/v1/health")
        body = response.json()
        assert "version" in body

    def test_404_unknown_route(self):
        response = self._client().get("/api/v1/nonexistent-endpoint-xyz")
        assert response.status_code == 404


# =========================================================================== #
# 7. KB VERSIONING TESTS                                                       #
# =========================================================================== #


class TestKBVersioning:
    def _store(self, tmp_path):
        from app.knowledge.kb_store import KBStore

        return KBStore(base_dir=tmp_path)

    def _create(self, store, title="SOP Test"):
        return store.create_kb(
            title=title,
            problem_statement="Test problem.",
            symptoms=["symptom A"],
            root_cause="Root cause A",
            evidence={"crc_errors": "1450"},
            resolution_steps=["Replace SFP"],
            validation_steps=["Ping test"],
            rollback_steps=["Restore backup"],
            created_by="engineer-001",
        )

    def test_create_kb_article(self, tmp_path):
        store = self._store(tmp_path)
        article = self._create(store)
        assert article.kb_id.startswith("KB-")
        assert article.version == "1.0"
        assert article.status.value == "DRAFT"

    def test_new_version_increments(self, tmp_path):
        store = self._store(tmp_path)
        v1 = self._create(store, "SOP v1")
        v2 = store.create_new_version(v1.kb_id, updated_by="eng-001", title="SOP v2")
        assert v2.version == "1.1"

    def test_old_version_is_immutable(self, tmp_path):
        store = self._store(tmp_path)
        v1 = self._create(store, "SOP Original")
        store.create_new_version(v1.kb_id, updated_by="eng-001", title="SOP Updated")
        # v1 must remain unchanged on disk
        v1_check = store.get_version(v1.kb_id, "1.0")
        assert v1_check.title == "SOP Original"

    def test_draft_to_pending_review(self, tmp_path):
        from app.models.kb_article import KBStatus

        store = self._store(tmp_path)
        article = self._create(store)
        updated = store.submit_for_review(article.kb_id, article.version)
        assert updated.status == KBStatus.PENDING_REVIEW

    def test_pending_review_to_approved(self, tmp_path):
        from app.models.kb_article import KBStatus

        store = self._store(tmp_path)
        article = self._create(store)
        store.submit_for_review(article.kb_id, article.version)
        approved = store.approve(article.kb_id, article.version, approved_by="lead-eng")
        assert approved.status == KBStatus.APPROVED

    def test_cannot_approve_draft_directly(self, tmp_path):
        """FAILURE CONDITION: invalid FSM transition – DRAFT→APPROVED must be rejected."""
        store = self._store(tmp_path)
        article = self._create(store)
        with pytest.raises(ValueError):
            # Approve without going through PENDING_REVIEW first
            store.approve(article.kb_id, article.version, approved_by="lead-eng")

    def test_version_history_length(self, tmp_path):
        store = self._store(tmp_path)
        v1 = self._create(store)
        store.create_new_version(v1.kb_id, updated_by="eng-001", title="SOP v2")
        history = store.get_version_history(v1.kb_id)
        assert len(history) == 2
        assert {h.version for h in history} == {"1.0", "1.1"}


# =========================================================================== #
# 8. VULNERABILITY MATCHING TESTS                                              #
# =========================================================================== #


class TestVulnerabilityMatching:
    def _service(self):
        from app.vulnerability.providers import MockVulnerabilityProvider
        from app.vulnerability.service import VulnerabilityService

        return VulnerabilityService(provider=MockVulnerabilityProvider())

    def test_known_device_model_returns_cves(self):
        service = self._service()
        # The mock dataset uses model name "Catalyst 9300" (exact match required)
        status = service.check_device(
            device_id="DEV-001",
            vendor="Cisco",
            device_model="Catalyst 9300",
            firmware_version="17.3.1",
        )
        assert status.cve_count > 0

    def test_unknown_device_returns_zero_cves(self):
        """FAILURE CONDITION: unknown_device – no CVEs claimed for unknown model."""
        service = self._service()
        status = service.check_device(
            device_id="DEV-UNKNOWN",
            vendor="Cisco",
            device_model="NonExistentRouter-9999",
            firmware_version="1.0.0",
        )
        assert status.cve_count == 0
        assert status.critical_cve_count == 0

    def test_invalid_firmware_version_returns_zero_cves(self):
        """FAILURE CONDITION: invalid_firmware – unrecognised version string → 0 CVEs."""
        service = self._service()
        status = service.check_device(
            device_id="DEV-002",
            vendor="Cisco",
            device_model="Catalyst 9300",
            firmware_version="INVALID_FIRMWARE_XYZ",
        )
        assert status.cve_count == 0

    def test_fabricated_cve_not_claimed(self):
        """FAILURE CONDITION: invalid_cve – fabricated CVE ID must never appear in results."""
        service = self._service()
        status = service.check_device(
            device_id="DEV-003",
            vendor="Cisco",
            device_model="Catalyst 9300",
            firmware_version="17.3.1",
        )
        cve_ids = [c.cve_id for c in status.cve_list]
        assert "CVE-9999-00001" not in cve_ids

    def test_cve_count_matches_cves_list(self):
        """Data integrity: cve_count must match len(cve_list)."""
        service = self._service()
        status = service.check_device(
            device_id="DEV-004",
            vendor="Cisco",
            device_model="Catalyst 9300",
            firmware_version="17.3.1",
        )
        assert status.cve_count == len(status.cve_list)

    def test_critical_count_subset_of_total(self):
        service = self._service()
        status = service.check_device(
            device_id="DEV-005",
            vendor="Cisco",
            device_model="Catalyst 9300",
            firmware_version="17.3.1",
        )
        assert status.critical_cve_count <= status.cve_count


# =========================================================================== #
# 9. LLM LAYER TESTS                                                           #
# =========================================================================== #


class TestLLMLayer:
    def _ctx(self, **kwargs):
        from app.llm.schemas import LLMContext, LLMTask

        defaults = dict(
            task=LLMTask.INCIDENT_SUMMARY,
            incident_id="INC-001",
            device_id="DEV-001",
            alert_type="NODE_DOWN",
            severity="CRITICAL",
            start_time="2023-01-01T10:00:00Z",
            probable_rca="Interface degradation",
            rca_confidence=0.9,
            rca_rule_id="RULE-001",
        )
        defaults.update(kwargs)
        return LLMContext(**defaults)

    def test_mock_provider_returns_string_without_api_key(self):
        """FAILURE CONDITION: llm_unavailable → MockProvider succeeds without API key."""
        from app.llm.providers import MockLLMProvider

        provider = MockLLMProvider()
        ctx = self._ctx()
        response = provider.complete(ctx)
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    def test_mock_provider_incident_summary(self):
        from app.llm.providers import MockLLMProvider
        from app.llm.schemas import LLMTask

        provider = MockLLMProvider()
        ctx = self._ctx(task=LLMTask.INCIDENT_SUMMARY)
        response = provider.complete(ctx)
        assert response is not None

    def test_llm_service_with_mock_provider(self):
        """LLM service orchestrates correctly using mock."""
        from app.llm.providers import MockLLMProvider
        from app.llm.schemas import LLMTask
        from app.llm.service import LLMService

        svc = LLMService(provider=MockLLMProvider())
        ctx = self._ctx(task=LLMTask.INCIDENT_SUMMARY)
        result = svc._invoke(ctx, LLMTask.INCIDENT_SUMMARY)
        assert result is not None

    def test_no_api_key_in_mock_provider(self):
        """Security: MockLLMProvider must not require or expose an API key."""
        import inspect

        from app.llm.providers import MockLLMProvider

        sig = inspect.signature(MockLLMProvider.__init__)
        param_names = list(sig.parameters.keys())
        assert "api_key" not in param_names


# =========================================================================== #
# 10. INTEGRATION TESTS                                                        #
# =========================================================================== #


class TestIntegration:
    def test_rca_parser_to_rca_engine(self):
        """Integration: parser output → RCA engine → deterministic result."""
        from app.rca.engine import DeterministicRCAEngine
        from app.rca.parser import CiscoRCAParser

        parser = CiscoRCAParser()
        engine = DeterministicRCAEngine()

        raw = """
        >> show interfaces Gi0/1
        Interface is UP
        CRC errors: 1450
        Interface flaps: 8

        >> show processes cpu
        CPU utilization: 42%

        >> show ip bgp summary
        10.0.0.2 4 65001 1434 1435 142 0 0 23:14:02 1
        """
        diag = parser.parse("INC-INT-001_rca.txt", raw)
        result = engine.evaluate("INC-INT-001", diag)

        assert result is not None
        assert result.probable_rca == "Interface degradation"
        assert "crc_errors" in result.evidence

    def test_full_predictive_pipeline_end_to_end(self, tmp_path):
        """Integration: feature data → train → predict → check output schema."""
        from app.predictive.ml_pipeline import MLPipeline

        base = datetime(2023, 1, 1)
        rows = [
            {
                "timestamp": base + timedelta(hours=i),
                "device_id": "DEV-001",
                "f1": 10.0 if i % 5 == 0 else 0.1,
                "f2": 50.0 if i % 5 == 0 else 0.5,
                "incident_next_7_days": 1 if i % 5 == 0 else 0,
            }
            for i in range(100)
        ]
        df = pd.DataFrame(rows)

        pipeline = MLPipeline(artifact_dir=tmp_path)
        pipeline.train_and_evaluate(df, ["f1", "f2"], "incident_next_7_days")

        new_row = pd.DataFrame([{
            "timestamp": base + timedelta(hours=101),
            "device_id": "DEV-001",
            "f1": 10.0,
            "f2": 50.0,
        }])
        predictions = pipeline.predict(new_row)

        assert len(predictions) == 1
        pred = predictions[0]
        assert 0.0 <= pred.failure_probability <= 1.0
        assert pred.device_id == "DEV-001"
        assert pred.risk_level is not None

    def test_kb_draft_from_rca_result(self, tmp_path):
        """Integration: RCA result → KB draft generator → valid article created."""
        from app.knowledge.kb_draft_generator import KBDraftGenerator
        from app.knowledge.kb_store import KBStore
        from app.rca.engine import DeterministicRCAEngine
        from app.rca.parser import CiscoRCAParser

        parser = CiscoRCAParser()
        engine = DeterministicRCAEngine()
        store = KBStore(base_dir=tmp_path)
        generator = KBDraftGenerator(store=store)

        raw = """
        >> show interfaces Gi0/1
        Interface is UP
        CRC errors: 1500
        Interface flaps: 12

        >> show processes cpu
        CPU utilization: 30%

        >> show ip bgp summary
        10.0.0.2 4 65001 100 100 10 0 0 01:00:00 5
        """
        diag = parser.parse("INC-KB-001_rca.txt", raw)
        rca_result = engine.evaluate("INC-KB-001", diag)

        assert rca_result is not None
        article = generator.generate_draft(
            rca_result=rca_result,
            created_by="engineer-001",
        )
        assert article is not None
        assert article.kb_id.startswith("KB-")
        assert article.status.value == "DRAFT"
