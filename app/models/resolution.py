"""Incident resolution and KPI tracking domain models."""

from datetime import datetime

from pydantic import BaseModel


class Resolution(BaseModel):
    """Engineer resolution of an incident."""
    incident_id: str
    device_id: str
    root_cause: str
    resolution_action: str
    validation_action: str
    resolved_by: str
    resolution_timestamp: datetime
    acknowledged_at: datetime
    diagnosed_at: datetime
    resolution_duration: float  # In minutes
    first_time_resolution: bool = True

class KPIReport(BaseModel):
    """Operational KPI Report."""
    total_incidents: int
    mtta_minutes: float
    mttd_minutes: float
    mttr_minutes: float
    ftr_rate: float
