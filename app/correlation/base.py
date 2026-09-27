"""Incident correlation engine interface definition."""

from typing import Protocol

from app.models.incident import (
    CiscoDiagnosticPayload,
    Incident,
    SolarWindsAlertEvent,
    SolarWindsRecoveryEvent,
)


class CorrelationEnginePort(Protocol):
    """Hexagonal Port: Manages sliding time-window stateful incident correlation."""

    def process_alert(self, alert: SolarWindsAlertEvent) -> Incident:
        """Initialize or update an incident based on an incoming alert."""
        ...

    def process_recovery(self, recovery: SolarWindsRecoveryEvent) -> Incident | None:
        """Correlate a recovery event to an existing active incident."""
        ...

    def attach_diagnostics(self, payload: CiscoDiagnosticPayload) -> Incident | None:
        """Associate diagnostic CLI command output to an open incident."""
        ...
