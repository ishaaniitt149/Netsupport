"""Simulator boundary interface."""

from typing import Protocol

from app.models.device import Device
from app.models.incident import (
    CiscoDiagnosticPayload,
    SolarWindsAlertEvent,
    SolarWindsRecoveryEvent,
)
from app.models.telemetry import TelemetryRecord


class SimulatorEnginePort(Protocol):
    """Hexagonal Port: Coordinates generation of synthetic network operations data."""

    def generate_inventory(self, count: int = 100) -> list[Device]:
        """Generate realistic Cisco device assets."""
        ...

    def generate_telemetry(self, device_id: str, days: int = 30) -> list[TelemetryRecord]:
        """Generate historical time-series telemetry snapshots."""
        ...

    def simulate_failure_scenario(
        self, scenario_name: str
    ) -> tuple[SolarWindsAlertEvent, SolarWindsRecoveryEvent, CiscoDiagnosticPayload]:
        """Simulate an end-to-end incident cycle with Cisco CLI output."""
        ...
