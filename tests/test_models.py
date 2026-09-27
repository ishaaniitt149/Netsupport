"""Tests for core domain entities and schema validation."""

from app.core.constants import IncidentState, Severity
from app.models.device import Device, TransceiverProfile
from app.models.incident import (
    CiscoDiagnosticPayload,
    Incident,
    SolarWindsAlertEvent,
    SolarWindsRecoveryEvent,
)
from app.models.prediction import DeviceRiskScore
from app.models.rca import RCAResult


def test_device_model_creation() -> None:
    """Verify creation and serialization of Device model with synthetic flag."""
    device = Device(
        device_id="dev-c9300-nyc-01",
        hostname="nyc-acc-sw01.corp.internal",
        ip_address="10.240.12.15",
        device_model="Cisco Catalyst 9300-48UXM",
        os_version="17.09.04a",
        serial_number="FOC2419X8KZ",
        site_code="NYC-HQ",
        transceivers=[
            TransceiverProfile(
                port_name="TenGigabitEthernet1/0/1",
                serial_number="OP-9812401",
            )
        ],
    )
    assert device.is_synthetic is True
    assert device.hostname == "nyc-acc-sw01.corp.internal"
    assert len(device.transceivers) == 1
    assert device.transceivers[0].port_name == "TenGigabitEthernet1/0/1"


def test_incident_and_events_models() -> None:
    """Verify Incident, SolarWinds Alert, Recovery, and Diagnostic models."""
    alert = SolarWindsAlertEvent(
        event_id="evt-001",
        alert_id="sw-alert-892147",
        device_hostname="nyc-acc-sw01.corp.internal",
        device_ip="10.240.12.15",
        trigger_condition="Packet loss > 80%",
        raw_email_subject="ALERT: Node Down",
        raw_email_body="Node Down Body",
    )
    assert alert.severity == Severity.CRITICAL
    assert alert.is_synthetic is True

    recovery = SolarWindsRecoveryEvent(
        event_id="evt-002",
        alert_id="sw-alert-892147",
        device_hostname="nyc-acc-sw01.corp.internal",
        device_ip="10.240.12.15",
        outage_duration_seconds=560.0,
        raw_email_subject="RECOVERY: Node Up",
        raw_email_body="Node Up Body",
    )
    assert recovery.outage_duration_seconds == 560.0

    diag = CiscoDiagnosticPayload(
        payload_id="diag-001",
        device_hostname="nyc-acc-sw01.corp.internal",
        device_ip="10.240.12.15",
        raw_cli_output="show interfaces output...",
    )
    assert diag.is_synthetic is True

    incident = Incident(
        incident_id="inc-20260927-0042",
        device_id="dev-c9300-nyc-01",
        device_hostname="nyc-acc-sw01.corp.internal",
        device_ip="10.240.12.15",
        state=IncidentState.ALERT_RECEIVED,
    )
    assert incident.state == IncidentState.ALERT_RECEIVED
    assert incident.first_time_resolved is True


def test_rca_and_risk_models() -> None:
    """Verify RCA and Risk Scoring models."""
    rca = RCAResult(
        rca_id="rca-001",
        incident_id="inc-20260927-0042",
        device_hostname="nyc-acc-sw01.corp.internal",
        matched_rule_id="R1-OPTICAL-DEGRADATION",
        category="PHYSICAL_OPTICAL",
        probable_cause="Optical Transceiver Degradation",
        confidence_score=0.96,
        evidence_citations=["Rx power is -19.4 dBm"],
        recommended_actions=["Replace SFP"],
    )
    assert rca.confidence_score == 0.96

    risk = DeviceRiskScore(
        score_id="risk-001",
        device_id="dev-c9300-nyc-01",
        device_hostname="nyc-acc-sw01.corp.internal",
        failure_probability_14d=0.88,
        vulnerability_penalty=0.65,
        telemetry_anomaly_penalty=0.92,
        composite_risk_score=83.25,
    )
    assert risk.composite_risk_score == 83.25
    assert risk.is_synthetic is True
