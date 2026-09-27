# Test for device generation
"""Unit tests for the synthetic device generator script."""

import csv
from pathlib import Path

from app.models.device import DeviceRecord
from scripts.generate_devices import generate_devices, write_devices_csv


def test_generate_devices_basic():
    devices = generate_devices(number_of_devices=10, random_seed=1)
    assert len(devices) == 10
    # Ensure all are instances of DeviceRecord and IDs are unique
    ids = {d.device_id for d in devices}
    assert len(ids) == 10
    for d in devices:
        assert isinstance(d, DeviceRecord)
        # generator only creates Cisco devices now
        assert d.vendor == "Cisco"
        assert len(d.serial_number) >= 10


def test_write_devices_csv(tmp_path: Path):
    devices = generate_devices(number_of_devices=5, random_seed=2)
    csv_path = tmp_path / "devices.csv"
    write_devices_csv(devices, csv_path)
    assert csv_path.exists()
    with csv_path.open(newline="") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 5
    # Header matches model fields
    expected_headers = list(DeviceRecord.model_fields.keys())
    assert list(reader[0].keys()) == expected_headers
