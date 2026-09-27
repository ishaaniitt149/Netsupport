"""Device inventory and synthetic device record models."""

from datetime import date

from pydantic import Field, field_validator

from app.models.base import PlatformBaseModel, TimestampedModel


class TransceiverProfile(TimestampedModel):
    """Optical transceiver profile installed in a device port."""

    port_name: str
    transceiver_type: str = "SFP-10G-SR"
    serial_number: str
    nominal_rx_threshold_dbm: float = -14.0
    nominal_tx_threshold_dbm: float = -1.0


class DeviceRecord(PlatformBaseModel):
    """Synthetic Cisco network device record matching inventory schema."""

    device_id: str = Field(description="Unique inventory identifier (e.g. DEV-CSCO-0001)")
    hostname: str = Field(description="Network FQDN / device hostname")
    vendor: str = Field(default="Cisco", description="Hardware vendor name")
    model: str = Field(description="Cisco hardware model")
    serial_number: str = Field(description="Cisco chassis serial number")
    firmware_version: str = Field(description="Operating system release version")
    location: str = Field(description="Facility or datacenter site location")
    region: str = Field(description="Geographic region")
    device_type: str = Field(description="Device functional role / type")
    criticality: str = Field(description="Business operational criticality level")
    interface_count: int = Field(ge=1, le=128, description="Total physical port count")
    last_patch_date: date = Field(description="Date of last maintenance or OS patch")
    customer: str = Field(description="Fictional customer or tenant organization")
    network_segment: str = Field(description="Network architectural segment / zone")

    @field_validator("vendor")
    @classmethod
    def validate_vendor(cls, v: str) -> str:
        if v.strip() != "Cisco":
            raise ValueError("Vendor must be Cisco")
        return v.strip()

    @field_validator("interface_count")
    @classmethod
    def validate_interface_count(cls, v: int) -> int:
        if v < 1 or v > 128:
            raise ValueError("Interface count must be between 1 and 128")
        return v


class Device(TimestampedModel):
    """Extended device asset entity with operational metadata."""

    device_id: str = Field(description="Unique inventory device identifier")
    hostname: str = Field(description="Fully qualified or network hostname")
    vendor: str = Field(default="Cisco", description="Hardware vendor")
    ip_address: str | None = Field(default=None, description="Management IP address")
    device_model: str = Field(description="Hardware platform (e.g. Cisco Catalyst 9300-48UXM)")
    os_type: str = Field(default="IOS-XE", description="Operating system family (IOS-XE, NX-OS)")
    os_version: str = Field(description="Active software image version")
    serial_number: str = Field(description="Chassis serial number")
    location: str | None = Field(default=None, description="Physical datacenter location")
    region: str | None = Field(default=None, description="Geographic region")
    site_code: str | None = Field(default=None, description="Enterprise site identifier")
    rack_location: str | None = Field(default=None, description="Rack identifier")
    role: str = Field(default="ACCESS", description="Network role (CORE, DIST, ACCESS, WAN)")
    criticality: str = Field(default="MEDIUM", description="Criticality rating")
    cve_vulnerabilities: list[str] = Field(default_factory=list, description="Known unpatched CVEs")
    transceivers: list[TransceiverProfile] = Field(default_factory=list)
