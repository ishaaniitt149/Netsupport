"""Synthetic Cisco Network Device Generator.

Produces realistic, reproducible, and verifiable Cisco network asset inventory
data for testing, simulation, and predictive maintenance development.
All generated records are marked with is_synthetic: True and use strictly
fictional customer names.
"""

from __future__ import annotations

import csv
import random
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from app.models.device import DeviceRecord


@dataclass(frozen=True)
class CiscoModelProfile:
    """Hardware profile archetype for realistic Cisco platforms."""

    model: str
    device_type: str
    interface_count: int
    firmware_versions: tuple[str, ...]
    preferred_segments: tuple[str, ...]


# Catalog of authentic Cisco platform archetypes
CISCO_PROFILES: tuple[CiscoModelProfile, ...] = (
    CiscoModelProfile(
        model="Cisco Catalyst 9300-48UXM",
        device_type="Access Switch",
        interface_count=48,
        firmware_versions=("17.09.04a", "17.06.05", "17.12.02"),
        preferred_segments=("CAMPUS-ACCESS", "BRANCH-OFFICE"),
    ),
    CiscoModelProfile(
        model="Cisco Catalyst 9200-24P",
        device_type="Access Switch",
        interface_count=24,
        firmware_versions=("17.09.03", "17.06.04", "17.09.04a"),
        preferred_segments=("CAMPUS-ACCESS", "BRANCH-OFFICE"),
    ),
    CiscoModelProfile(
        model="Cisco Catalyst 9500-48Y4C",
        device_type="Core Switch",
        interface_count=52,
        firmware_versions=("17.09.04a", "17.12.01", "17.09.05"),
        preferred_segments=("CORE-BACKBONE", "DC-FABRIC"),
    ),
    CiscoModelProfile(
        model="Cisco Catalyst 9500-24Q",
        device_type="Distribution Switch",
        interface_count=24,
        firmware_versions=("17.09.03", "17.06.05", "17.09.04a"),
        preferred_segments=("CORE-BACKBONE", "CAMPUS-ACCESS"),
    ),
    CiscoModelProfile(
        model="Cisco Nexus 93180YC-FX",
        device_type="Data Center Switch",
        interface_count=54,
        firmware_versions=("10.3(4a)M", "9.3(10)", "10.2(5)M"),
        preferred_segments=("DC-FABRIC", "CORE-BACKBONE"),
    ),
    CiscoModelProfile(
        model="Cisco Nexus 9336C-FX2",
        device_type="Data Center Spine",
        interface_count=36,
        firmware_versions=("10.3(3)F", "9.3(9)", "10.2(5)M"),
        preferred_segments=("DC-FABRIC", "CORE-BACKBONE"),
    ),
    CiscoModelProfile(
        model="Cisco ISR 4451-X",
        device_type="WAN Router",
        interface_count=8,
        firmware_versions=("17.06.05", "17.09.04a", "17.03.07"),
        preferred_segments=("WAN-EDGE", "BRANCH-OFFICE"),
    ),
    CiscoModelProfile(
        model="Cisco Catalyst 8300-2N2S-4T2X",
        device_type="SD-WAN Edge Router",
        interface_count=12,
        firmware_versions=("17.09.04a", "17.11.01a", "17.12.02"),
        preferred_segments=("WAN-EDGE", "BRANCH-OFFICE"),
    ),
    CiscoModelProfile(
        model="Cisco ASR 1001-X",
        device_type="Aggregation Router",
        interface_count=8,
        firmware_versions=("17.06.05", "17.09.04a", "16.12.08"),
        preferred_segments=("WAN-EDGE", "CORE-BACKBONE"),
    ),
    CiscoModelProfile(
        model="Cisco Firepower 2130",
        device_type="Security Gateway",
        interface_count=16,
        firmware_versions=("7.2.5", "7.4.1", "7.0.6"),
        preferred_segments=("DMZ-SECURITY", "WAN-EDGE"),
    ),
)

LOCATIONS: tuple[tuple[str, str, str], ...] = (
    ("New York Data Center", "AMER-EAST", "nyc"),
    ("San Jose Campus", "AMER-WEST", "sjc"),
    ("Chicago Colocation", "AMER-CENTRAL", "chi"),
    ("London Docklands DC", "EMEA-WEST", "lon"),
    ("Frankfurt Cloud Gateway", "EMEA-CENTRAL", "fra"),
    ("Amsterdam Data Hub", "EMEA-WEST", "ams"),
    ("Singapore Equinix DC", "APAC-SOUTH", "sin"),
    ("Tokyo Regional Hub", "APAC-EAST", "tko"),
    ("Sydney Edge Facility", "APAC-SOUTH", "syd"),
    ("Toronto Enterprise Site", "AMER-EAST", "tor"),
)

CRITICALITY_LEVELS: tuple[str, ...] = ("CRITICAL", "HIGH", "MEDIUM", "LOW")

FICTIONAL_CUSTOMERS: tuple[str, ...] = (
    "Apex Global Logistics",
    "Horizon Health Systems",
    "Starlight Financial Group",
    "Zenith Retail Group",
    "OmniTech Industries",
    "Vanguard Energy Corp",
    "Novus Media Works",
    "Pinnacle BioLabs",
    "Beacon Automotive",
    "Strata Cloud Solutions",
    "Aegis Defense Labs",
    "Solaria Renewable Power",
)

SERIAL_FACTORIES: tuple[str, ...] = ("FOC", "JAE", "SAL", "FOX", "REF")


@dataclass
class DeviceGeneratorConfig:
    """Configuration parameters for deterministic device inventory generation."""

    number_of_devices: int = 100
    random_seed: int = 42
    start_date: date = date(2026, 1, 1)


@dataclass
class ValidationReport:
    """Summary of data integrity checks executed on the generated dataset."""

    total_records: int
    is_valid: bool
    errors: list[str]
    unique_device_ids: int
    unique_hostnames: int
    unique_serials: int


class CiscoDeviceGenerator:
    """Deterministic generator for synthetic Cisco network devices."""

    def __init__(self, config: DeviceGeneratorConfig | None = None) -> None:
        self.config = config or DeviceGeneratorConfig()
        self._rng = random.Random(self.config.random_seed)

    def generate(self) -> list[DeviceRecord]:
        """Generate the configured list of DeviceRecord entities."""
        # Re-seed RNG for guaranteed reproducibility
        self._rng.seed(self.config.random_seed)

        devices: list[DeviceRecord] = []
        used_ids: set[str] = set()
        used_hostnames: set[str] = set()
        used_serials: set[str] = set()

        for idx in range(1, self.config.number_of_devices + 1):
            device_id = f"DEV-CSCO-{idx:04d}"
            profile = self._rng.choice(CISCO_PROFILES)
            location, region, site_code = self._rng.choice(LOCATIONS)
            segment = self._rng.choice(profile.preferred_segments)

            # Generate unique serial number (Cisco 11-char format: 3-letter factory + 2-digit year + 2-digit week + 4 alphanumeric)
            serial = self._generate_unique_serial(used_serials)

            # Generate unique hostname
            role_slug = self._get_role_slug(profile.device_type)
            hostname = self._generate_unique_hostname(site_code, role_slug, idx, used_hostnames)

            # Select firmware version compatible with model
            firmware = self._rng.choice(profile.firmware_versions)

            # Weight criticality based on device role
            criticality = self._assign_criticality(profile.device_type, segment)

            # Calculate a realistic last patch date within 180 days prior to start_date
            days_prior = self._rng.randint(5, 180)
            last_patch_date = self.config.start_date - timedelta(days=days_prior)

            # Select fictional customer
            customer = self._rng.choice(FICTIONAL_CUSTOMERS)

            record = DeviceRecord(
                device_id=device_id,
                hostname=hostname,
                vendor="Cisco",
                model=profile.model,
                serial_number=serial,
                firmware_version=firmware,
                location=location,
                region=region,
                device_type=profile.device_type,
                criticality=criticality,
                interface_count=profile.interface_count,
                last_patch_date=last_patch_date,
                customer=customer,
                network_segment=segment,
                is_synthetic=True,
            )

            used_ids.add(device_id)
            used_hostnames.add(hostname)
            used_serials.add(serial)
            devices.append(record)

        return devices

    def generate_csv(self, output_path: Path | str) -> Path:
        """Generate devices and persist directly to a standard CSV file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        devices = self.generate()

        fieldnames = [
            "device_id",
            "hostname",
            "vendor",
            "model",
            "serial_number",
            "firmware_version",
            "location",
            "region",
            "device_type",
            "criticality",
            "interface_count",
            "last_patch_date",
            "customer",
            "network_segment",
        ]

        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for dev in devices:
                writer.writerow(
                    {
                        "device_id": dev.device_id,
                        "hostname": dev.hostname,
                        "vendor": dev.vendor,
                        "model": dev.model,
                        "serial_number": dev.serial_number,
                        "firmware_version": dev.firmware_version,
                        "location": dev.location,
                        "region": dev.region,
                        "device_type": dev.device_type,
                        "criticality": dev.criticality,
                        "interface_count": dev.interface_count,
                        "last_patch_date": dev.last_patch_date.isoformat(),
                        "customer": dev.customer,
                        "network_segment": dev.network_segment,
                    }
                )

        return path

    def validate_dataset(self, devices: list[DeviceRecord]) -> ValidationReport:
        """Run extensive validation checks against the generated dataset."""
        errors: list[str] = []

        if len(devices) != self.config.number_of_devices:
            errors.append(f"Expected {self.config.number_of_devices} records, got {len(devices)}")

        ids = [d.device_id for d in devices]
        hostnames = [d.hostname for d in devices]
        serials = [d.serial_number for d in devices]

        if len(ids) != len(set(ids)):
            errors.append("Duplicate device_ids found in dataset")
        if len(hostnames) != len(set(hostnames)):
            errors.append("Duplicate hostnames found in dataset")
        if len(serials) != len(set(serials)):
            errors.append("Duplicate serial_numbers found in dataset")

        # Serial number format validation (Cisco 11-character regex)
        serial_pattern = re.compile(r"^[A-Z]{3}\d{4}[A-Z0-9]{4}$")
        for dev in devices:
            if not serial_pattern.match(dev.serial_number):
                errors.append(
                    f"Invalid Cisco serial format for {dev.device_id}: {dev.serial_number}"
                )

            if dev.vendor != "Cisco":
                errors.append(f"Invalid vendor for {dev.device_id}: {dev.vendor}")

            if dev.interface_count < 1 or dev.interface_count > 128:
                errors.append(
                    f"Unrealistic interface count for {dev.device_id}: {dev.interface_count}"
                )

            if dev.last_patch_date > self.config.start_date:
                errors.append(f"Patch date in future relative to start_date for {dev.device_id}")

            if dev.criticality not in CRITICALITY_LEVELS:
                errors.append(f"Invalid criticality for {dev.device_id}: {dev.criticality}")

        return ValidationReport(
            total_records=len(devices),
            is_valid=len(errors) == 0,
            errors=errors,
            unique_device_ids=len(set(ids)),
            unique_hostnames=len(set(hostnames)),
            unique_serials=len(set(serials)),
        )

    def _generate_unique_serial(self, used: set[str]) -> str:
        chars = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        while True:
            factory = self._rng.choice(SERIAL_FACTORIES)
            year = self._rng.randint(23, 26)  # 2023 - 2026
            week = self._rng.randint(1, 52)
            suffix = "".join(self._rng.choices(chars, k=4))
            candidate = f"{factory}{year:02d}{week:02d}{suffix}"
            if candidate not in used:
                return candidate

    def _generate_unique_hostname(self, site: str, role: str, idx: int, used: set[str]) -> str:
        candidate = f"{site}-{role}-{idx:03d}.corp.internal"
        if candidate in used:
            counter = 1
            while f"{site}-{role}-{idx:03d}-{counter}.corp.internal" in used:
                counter += 1
            candidate = f"{site}-{role}-{idx:03d}-{counter}.corp.internal"
        return candidate

    def _get_role_slug(self, device_type: str) -> str:
        mapping = {
            "Core Switch": "core-sw",
            "Distribution Switch": "dist-sw",
            "Access Switch": "acc-sw",
            "Data Center Switch": "dc-sw",
            "Data Center Spine": "spine-sw",
            "WAN Router": "wan-rtr",
            "SD-WAN Edge Router": "sdw-rtr",
            "Aggregation Router": "agg-rtr",
            "Security Gateway": "sec-gw",
        }
        return mapping.get(device_type, "net-dev")

    def _assign_criticality(self, device_type: str, segment: str) -> str:
        if "Core" in device_type or "Spine" in device_type or segment == "CORE-BACKBONE":
            return self._rng.choices(["CRITICAL", "HIGH"], weights=[0.8, 0.2])[0]
        if "Security" in device_type or segment == "DMZ-SECURITY":
            return self._rng.choices(["CRITICAL", "HIGH", "MEDIUM"], weights=[0.6, 0.3, 0.1])[0]
        if "WAN" in device_type or "Aggregation" in device_type:
            return self._rng.choices(["HIGH", "MEDIUM"], weights=[0.7, 0.3])[0]
        return self._rng.choices(["MEDIUM", "LOW"], weights=[0.6, 0.4])[0]
