"""Incident, alert, recovery, and diagnostic payload domain models."""

from datetime import datetime

from pydantic import Field

from app.core.constants import IncidentState, Severity
from app.models.base import PlatformBaseModel, TimestampedModel, get_utc_now


class SolarWindsAlertEvent(PlatformBaseModel):
    """SolarWinds node outage or degradation alert."""

    event_id: str
    source_system: str = "SolarWinds-NPM"
    alert_id: str
    alert_name: str = "Node Down Alert"
    severity: Severity = Severity.CRITICAL
    device_hostname: str
    device_ip: str
    timestamp: datetime = Field(default_factory=get_utc_now)
    trigger_condition: str
    raw_email_subject: str
    raw_email_body: str


class SolarWindsRecoveryEvent(PlatformBaseModel):
    """SolarWinds node recovery event."""

    event_id: str
    source_system: str = "SolarWinds-NPM"
    alert_id: str
    device_hostname: str
    device_ip: str
    recovery_timestamp: datetime = Field(default_factory=get_utc_now)
    outage_duration_seconds: float = 0.0
    raw_email_subject: str
    raw_email_body: str


class CiscoDiagnosticPayload(PlatformBaseModel):
    """Cisco CLI diagnostic output captured by automated recovery script."""

    payload_id: str
    device_hostname: str
    device_ip: str
    execution_timestamp: datetime = Field(default_factory=get_utc_now)
    executed_commands: list[str] = Field(default_factory=list)
    raw_cli_output: str


class Incident(TimestampedModel):
    """Correlated operational incident entity."""

    incident_id: str
    device_id: str
    device_hostname: str
    device_ip: str
    state: IncidentState = IncidentState.ALERT_RECEIVED
    severity: Severity = Severity.CRITICAL

    # Timestamps for operational KPI tracking
    alert_timestamp: datetime = Field(default_factory=get_utc_now)
    recovery_timestamp: datetime | None = None
    diagnostics_attached_at: datetime | None = None
    rca_completed_at: datetime | None = None
    resolved_at: datetime | None = None

    outage_duration_sec: float | None = None
    first_time_resolved: bool = True
    applied_kb_doc_id: str | None = None
    resolution_notes: str | None = None
