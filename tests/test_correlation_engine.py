"""Unit tests for the incident correlation engine."""

from pathlib import Path

import pandas as pd

from app.correlation.engine import CorrelationEngine


def test_correlate_incidents(tmp_path: Path):
    events_csv = tmp_path / "events.csv"
    rca_meta_csv = tmp_path / "metadata.csv"
    output_parquet = tmp_path / "incidents.parquet"

    # Create test data
    events_csv.write_text(
        "event_id,device_id,event_type,severity,timestamp\n"
        "E1,DEV-001,PACKET_LOSS,warning,2023-01-01T10:00:00Z\n"
        "E2,DEV-001,NODE_DOWN,critical,2023-01-01T10:05:00Z\n"  # upgraded severity
        "E3,DEV-001,RECOVERY,info,2023-01-01T10:20:00Z\n"
        "E4,DEV-002,NODE_DOWN,critical,2023-01-01T11:00:00Z\n"  # no recovery
        "E5,DEV-003,NODE_DOWN,critical,2023-01-01T12:00:00Z\n"
        "E6,DEV-003,NODE_DOWN,critical,2023-01-01T12:01:00Z\n"  # duplicate
        "E7,DEV-003,NODE_UP,info,2023-01-01T12:10:00Z\n",
        encoding="utf-8"
    )

    rca_meta_csv.write_text(
        "incident_id,device_id,rca_file,alert_event_id,recovery_event_id\n"
        "INC-123,DEV-001,rca_1.txt,E1,E3\n",
        encoding="utf-8"
    )

    engine = CorrelationEngine(events_csv, rca_meta_csv, output_parquet)
    incidents = engine.run()

    # 3 incidents should be created (DEV-001, DEV-002, DEV-003)
    assert len(incidents) == 3

    # Incident 1 (DEV-001): PACKET_LOSS -> NODE_DOWN -> RECOVERY + RCA
    inc_1 = next(i for i in incidents if i.device_id == "DEV-001")
    assert inc_1.alert_type == "NODE_DOWN"  # upgraded
    assert inc_1.severity == "critical"
    assert inc_1.duration_minutes == 20.0
    assert inc_1.rca_source == "rca_1.txt"
    assert inc_1.correlation_confidence == 1.0

    # Incident 2 (DEV-002): NODE_DOWN without recovery
    inc_2 = next(i for i in incidents if i.device_id == "DEV-002")
    assert inc_2.recovery_time is None
    assert inc_2.duration_minutes is None
    assert inc_2.rca_source is None
    assert inc_2.correlation_confidence == 0.5

    # Incident 3 (DEV-003): NODE_DOWN (duplicate) -> NODE_UP without RCA
    inc_3 = next(i for i in incidents if i.device_id == "DEV-003")
    assert inc_3.duration_minutes == 10.0
    assert inc_3.rca_source is None
    assert inc_3.correlation_confidence == 0.8

    # Verify parquet was saved
    assert output_parquet.exists()
    df = pd.read_parquet(output_parquet)
    assert len(df) == 3
