"""Device inventory and hardware profile models."""


from pydantic import Field

from app.models.base import TimestampedModel


class TransceiverProfile(TimestampedModel):
    port_name: str
    transceiver_type: str = "SFP-10G-SR"
    serial_number: str
    nominal_rx_threshold_dbm: float = -14.0
    nominal_tx_threshold_dbm: float = -1.0


class Device(TimestampedModel):
    """Cisco device inventory asset entity."""

    device_id: str = Field(description="Unique inventory device identifier")
    hostname: str = Field(description="Fully qualified or network hostname")
    ip_address: str = Field(description="Primary management IP address")
    device_model: str = Field(description="Hardware platform (e.g. Cisco Catalyst 9300-48UXM)")
    os_type: str = Field(default="IOS-XE", description="Operating system family (IOS-XE, NX-OS)")
    os_version: str = Field(description="Active software image version")
    serial_number: str = Field(description="Chassis serial number")
    site_code: str = Field(description="Enterprise site identifier (e.g. NYC-HQ, LON-DC)")
    rack_location: str | None = Field(default=None, description="Physical datacenter location")
    role: str = Field(default="ACCESS", description="Network role (CORE, DIST, ACCESS, WAN)")
    cve_vulnerabilities: list[str] = Field(default_factory=list, description="Known unpatched CVEs")
    transceivers: list[TransceiverProfile] = Field(default_factory=list)
