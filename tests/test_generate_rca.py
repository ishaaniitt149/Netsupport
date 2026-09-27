"""Unit tests for the synthetic Cisco RCA generator."""

import csv
from pathlib import Path

from scripts.generate_rca import extract_incidents, generate_rca_text, generate_rcas


def test_generate_rca_text():
    # Test PACKET_LOSS scenario
    text_pl = generate_rca_text("DEV-001", "PACKET_LOSS", "2023-01-01T12:00:00Z")
    assert "Interface is UP" in text_pl
    assert "CRC errors: 1450" in text_pl
    assert "Input errors: 1510" in text_pl

    # Test NODE_DOWN scenario
    text_nd = generate_rca_text("DEV-002", "NODE_DOWN", "2023-01-01T12:00:00Z")
    assert "CRC errors: 0" in text_nd


def test_extract_incidents():
    events = [
        {"device_id": "D1", "event_type": "NODE_DOWN", "event_id": "E1", "timestamp": "2023-01-01T12:00:00Z"},
        {"device_id": "D1", "event_type": "NODE_UP", "event_id": "E2", "timestamp": "2023-01-01T12:10:00Z"},
        {"device_id": "D2", "event_type": "PACKET_LOSS", "event_id": "E3", "timestamp": "2023-01-01T12:00:00Z"},
        {"device_id": "D2", "event_type": "RECOVERY", "event_id": "E4", "timestamp": "2023-01-01T12:10:00Z"},
    ]

    incidents = extract_incidents(events)
    assert len(incidents) == 2

    for inc in incidents:
        assert inc["incident_id"].startswith("INC-")
        assert "device_id" in inc
        assert "alert_event_id" in inc
        assert "recovery_event_id" in inc


def test_generate_rcas(tmp_path: Path):
    events_csv = tmp_path / "events.csv"
    events_csv.write_text(
        "device_id,event_type,event_id,timestamp\n"
        "D1,NODE_DOWN,E1,2023-01-01T12:00:00Z\n"
        "D1,NODE_UP,E2,2023-01-01T12:10:00Z\n",
        encoding="utf-8"
    )

    rca_dir = tmp_path / "rca_emails"
    num = generate_rcas(events_csv, rca_dir)
    assert num == 1

    metadata_path = rca_dir / "metadata.csv"
    assert metadata_path.exists()

    with metadata_path.open("r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        rca_file = reader[0]["rca_file"]

    assert (rca_dir / rca_file).exists()

    text = (rca_dir / rca_file).read_text(encoding="utf-8")
    assert "RCA Diagnostic Report for D1" in text
