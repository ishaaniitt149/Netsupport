"""Predictive maintenance, risk scoring, and proactive work order models."""

from datetime import datetime

from pydantic import Field

from app.core.constants import RiskCategory
from app.models.base import TimestampedModel, get_utc_now


class DeviceRiskScore(TimestampedModel):
    """Device failure probability and composite risk score."""

    score_id: str
    device_id: str
    device_hostname: str
    failure_probability_14d: float = Field(ge=0.0, le=1.0)
    vulnerability_penalty: float = Field(ge=0.0, le=1.0)
    telemetry_anomaly_penalty: float = Field(ge=0.0, le=1.0)
    composite_risk_score: float = Field(ge=0.0, le=100.0)
    risk_category: RiskCategory = RiskCategory.LOW
    top_risk_factors: list[str] = Field(default_factory=list)
    recommended_preventive_action: str | None = None
    scored_at: datetime = Field(default_factory=get_utc_now)


class PreventiveTicket(TimestampedModel):
    """Proactive maintenance ticket created before outage occurs."""

    ticket_id: str
    device_id: str
    device_hostname: str
    risk_score: float
    preventive_action_type: str
    status: str = "OPEN"
    target_completion_date: datetime | None = None
    assigned_group: str = "Network Engineering L3"
    notes: str | None = None
