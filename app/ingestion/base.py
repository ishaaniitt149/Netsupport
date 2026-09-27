"""Event ingestion port interface definition."""

from collections.abc import Iterator
from typing import Protocol

from app.models.incident import (
    CiscoDiagnosticPayload,
    SolarWindsAlertEvent,
    SolarWindsRecoveryEvent,
)


class EventIngestionPort(Protocol):
    """Hexagonal Port: Decouples event ingestion transport from core platform.

    Can be backed by SyntheticEventAdapter (today) or M365GraphAPIAdapter (tomorrow)
    without changing core correlation logic.
    """

    def poll_alerts(self, batch_size: int = 50) -> Iterator[SolarWindsAlertEvent]:
        """Poll or yield incoming alert events."""
        ...

    def poll_recoveries(self, batch_size: int = 50) -> Iterator[SolarWindsRecoveryEvent]:
        """Poll or yield incoming recovery notifications."""
        ...

    def poll_diagnostics(self, batch_size: int = 50) -> Iterator[CiscoDiagnosticPayload]:
        """Poll or yield incoming post-recovery Cisco CLI diagnostic script dumps."""
        ...
