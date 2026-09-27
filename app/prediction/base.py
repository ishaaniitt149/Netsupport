"""Predictive maintenance and risk scoring interface."""

from typing import Protocol

from app.models.device import Device
from app.models.prediction import DeviceRiskScore, PreventiveTicket
from app.models.telemetry import TelemetryRecord


class PredictionEnginePort(Protocol):
    """Hexagonal Port: Evaluates failure likelihood and ranks Top 10 high-risk devices."""

    def calculate_risk_score(
        self, device: Device, telemetry_history: list[TelemetryRecord]
    ) -> DeviceRiskScore:
        """Calculate composite risk score (0-100) for a device."""
        ...

    def get_top_at_risk_devices(self, limit: int = 10) -> list[DeviceRiskScore]:
        """Rank and return top N highest risk network assets."""
        ...

    def generate_preventive_ticket(self, risk_score: DeviceRiskScore) -> PreventiveTicket:
        """Create proactive work order based on risk factors."""
        ...
