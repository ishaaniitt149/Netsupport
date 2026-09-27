"""Telemetry and time-series observation data models."""

from datetime import datetime

from pydantic import Field

from app.models.base import PlatformBaseModel, get_utc_now


class InterfaceTelemetry(PlatformBaseModel):
    interface_name: str
    status: str = "UP"
    in_octets_rate: float = 0.0
    out_octets_rate: float = 0.0
    input_crc_errors: int = 0
    input_errors_delta: int = 0
    rx_optical_power_dbm: float | None = None
    tx_optical_power_dbm: float | None = None
    link_flaps_delta: int = 0


class TelemetryRecord(PlatformBaseModel):
    """Periodic telemetry snapshot collected for a device."""

    telemetry_id: str
    device_id: str
    timestamp: datetime = Field(default_factory=get_utc_now)
    cpu_util_pct_5m: float = 0.0
    memory_used_bytes: int = 0
    memory_free_bytes: int = 0
    temperature_inlet_c: float = 25.0
    temperature_asic_c: float = 45.0
    psu1_status: str = "NORMAL"
    psu2_status: str = "NORMAL"
    interfaces: list[InterfaceTelemetry] = Field(default_factory=list)
