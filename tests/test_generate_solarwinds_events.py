"""Unit tests for the synthetic SolarWinds events generator."""

import csv
import json
from datetime import datetime
from pathlib import Path

from app.models.device import DeviceRecord
from scripts.generate_solarwinds_events import generate_events, write_events_csv, write_events_jsonl


def get_mock_device() -> DeviceRecord:
    return DeviceRecord(
        device_id="dev-test-001",
        hostname="test-router-01",
        vendor="Cisco",
        model="CIS-1000",
        serial_number="ABC12345678",
        firmware_version="15.2(3)E6",
        location="Test Lab",
        region="us-east-1",
        device_type="Router",
        criticality="High",
        interface_count=24,
        last_patch_date=datetime(2023, 1, 1).date(),
        customer="Test Inc",
        network_segment="10.0.0.0/24",
    )


def test_generate_events():
    device = get_mock_device()
    # Force an incident for this device by setting incident_rate to 1.0
    events = generate_events([device], incident_rate=1.0, random_seed=42)

    assert len(events) == 4
    types = [e["event_type"] for e in events]
    assert "PACKET_LOSS" in types
    assert "NODE_DOWN" in types
    assert "RECOVERY" in types
    assert "NODE_UP" in types

    # Check schema
    for event in events:
        assert "event_id" in event
        assert event["device_id"] == "dev-test-001"
        assert event["correlation_key"] == "dev-test-001"
        assert event["source"] == "SolarWinds"
        assert "severity" in event
        assert "timestamp" in event
        assert "message" in event

def test_generate_events_no_incidents():
    device = get_mock_device()
    # Force no incident
    events = generate_events([device], incident_rate=0.0, random_seed=42)
    assert len(events) == 0

def test_write_events(tmp_path: Path):
    device = get_mock_device()
    events = generate_events([device], incident_rate=1.0, random_seed=42)

    json_path = tmp_path / "events.jsonl"
    csv_path = tmp_path / "events.csv"

    write_events_jsonl(events, json_path)
    write_events_csv(events, csv_path)

    assert json_path.exists()
    assert csv_path.exists()

    # verify JSONL
    with json_path.open("r") as f:
        lines = f.readlines()
        assert len(lines) == 4
        parsed = json.loads(lines[0])
        assert parsed["device_id"] == "dev-test-001"

    # verify CSV
    with csv_path.open("r", newline="") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 4
        assert reader[0]["device_id"] == "dev-test-001"
