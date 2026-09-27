"""Unit tests for the synthetic Cisco network device generator."""

import csv
import re
from datetime import date
from pathlib import Path

from simulator.device_generator import (
    CiscoDeviceGenerator,
    DeviceGeneratorConfig,
    ValidationReport,
)


def test_default_generation_100_devices() -> None:
    """Verify that default configuration produces exactly 100 valid devices."""
    generator = CiscoDeviceGenerator()
    devices = generator.generate()

    assert len(devices) == 100
    for dev in devices:
        assert dev.vendor == "Cisco"
        assert dev.is_synthetic is True
        assert dev.device_id.startswith("DEV-CSCO-")
        assert len(dev.serial_number) == 11
        assert dev.interface_count in (8, 12, 16, 24, 36, 48, 52, 54)


def test_deterministic_reproducibility() -> None:
    """Verify that identical random seeds produce identical datasets."""
    config_a = DeviceGeneratorConfig(number_of_devices=25, random_seed=42)
    config_b = DeviceGeneratorConfig(number_of_devices=25, random_seed=42)

    devices_a = CiscoDeviceGenerator(config_a).generate()
    devices_b = CiscoDeviceGenerator(config_b).generate()

    assert len(devices_a) == len(devices_b)
    for dev_a, dev_b in zip(devices_a, devices_b, strict=True):
        assert dev_a.device_id == dev_b.device_id
        assert dev_a.hostname == dev_b.hostname
        assert dev_a.serial_number == dev_b.serial_number
        assert dev_a.model == dev_b.model
        assert dev_a.firmware_version == dev_b.firmware_version
        assert dev_a.last_patch_date == dev_b.last_patch_date
        assert dev_a.customer == dev_b.customer


def test_different_seeds_produce_different_data() -> None:
    """Verify that differing random seeds generate different device attributes."""
    config_a = DeviceGeneratorConfig(number_of_devices=10, random_seed=42)
    config_b = DeviceGeneratorConfig(number_of_devices=10, random_seed=999)

    devices_a = CiscoDeviceGenerator(config_a).generate()
    devices_b = CiscoDeviceGenerator(config_b).generate()

    serials_a = [d.serial_number for d in devices_a]
    serials_b = [d.serial_number for d in devices_b]
    assert serials_a != serials_b


def test_configurable_device_count() -> None:
    """Verify configurability of number_of_devices."""
    for count in (1, 10, 50, 150):
        config = DeviceGeneratorConfig(number_of_devices=count, random_seed=123)
        devices = CiscoDeviceGenerator(config).generate()
        assert len(devices) == count
        assert devices[0].device_id == "DEV-CSCO-0001"
        assert devices[-1].device_id == f"DEV-CSCO-{count:04d}"


def test_configurable_start_date() -> None:
    """Verify that start_date constrains last_patch_date properly."""
    custom_start = date(2025, 6, 1)
    config = DeviceGeneratorConfig(number_of_devices=30, random_seed=42, start_date=custom_start)
    generator = CiscoDeviceGenerator(config)
    devices = generator.generate()

    for dev in devices:
        assert dev.last_patch_date <= custom_start
        # Patch date should be within 180 days prior to start_date
        assert (custom_start - dev.last_patch_date).days <= 180


def test_validation_checks_pass() -> None:
    """Verify that the built-in validation checks succeed on generated data."""
    generator = CiscoDeviceGenerator(DeviceGeneratorConfig(number_of_devices=100, random_seed=42))
    devices = generator.generate()
    report: ValidationReport = generator.validate_dataset(devices)

    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.total_records == 100
    assert report.unique_device_ids == 100
    assert report.unique_hostnames == 100
    assert report.unique_serials == 100


def test_serial_format_cisco_regex() -> None:
    """Verify Cisco 11-character chassis serial number format compliance."""
    serial_pattern = re.compile(r"^[A-Z]{3}\d{4}[A-Z0-9]{4}$")
    generator = CiscoDeviceGenerator(DeviceGeneratorConfig(number_of_devices=50, random_seed=101))
    devices = generator.generate()

    for dev in devices:
        assert serial_pattern.match(dev.serial_number), (
            f"Serial {dev.serial_number} does not match Cisco 11-char regex"
        )


def test_csv_export_and_reading(tmp_path: Path) -> None:
    """Verify writing to CSV and validating content, headers, and row counts."""
    csv_file = tmp_path / "test_devices.csv"
    generator = CiscoDeviceGenerator(DeviceGeneratorConfig(number_of_devices=20, random_seed=42))

    written_path = generator.generate_csv(csv_file)
    assert written_path.exists()

    with open(written_path, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 20
    expected_headers = [
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
    assert list(reader[0].keys()) == expected_headers

    # Check sample row values
    row0 = reader[0]
    assert row0["device_id"] == "DEV-CSCO-0001"
    assert row0["vendor"] == "Cisco"
    assert int(row0["interface_count"]) > 0
    assert len(row0["serial_number"]) == 11
    assert row0["customer"] != ""
