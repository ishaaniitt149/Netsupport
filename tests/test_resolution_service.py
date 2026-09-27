"""Unit tests for the resolution service."""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from app.models.resolution import Resolution
from app.services.resolution_service import ResolutionService


def test_resolution_crud(tmp_path: Path):
    parquet_path = tmp_path / "resolutions.parquet"
    service = ResolutionService(parquet_path)

    start_time = datetime(2023, 1, 1, 10, 0)

    # Test Create
    res = Resolution(
        incident_id="INC-111",
        device_id="DEV-001",
        root_cause="Test issue",
        resolution_action="Test fix",
        validation_action="Test validation",
        resolved_by="Engineer A",
        resolution_timestamp=start_time + timedelta(minutes=45),
        acknowledged_at=start_time + timedelta(minutes=5),
        diagnosed_at=start_time + timedelta(minutes=20),
        resolution_duration=45.0,
        first_time_resolution=True
    )

    service.create_resolution(res)
    assert parquet_path.exists()

    # Test Get
    retrieved = service.get_resolution("INC-111")
    assert retrieved is not None
    assert retrieved.incident_id == "INC-111"
    assert retrieved.root_cause == "Test issue"

    # Test Update
    updated = service.update_resolution("INC-111", {"root_cause": "Updated issue", "first_time_resolution": False})
    assert updated.root_cause == "Updated issue"
    assert updated.first_time_resolution is False

    # Verify persistance
    service_reloaded = ResolutionService(parquet_path)
    reloaded = service_reloaded.get_resolution("INC-111")
    assert reloaded.root_cause == "Updated issue"


def test_calculate_kpis(tmp_path: Path):
    parquet_path = tmp_path / "resolutions.parquet"
    service = ResolutionService(parquet_path)

    start_time = datetime(2023, 1, 1, 10, 0)

    incidents_data = [
        {"incident_id": "INC-1", "device_id": "D1", "start_time": start_time},
        {"incident_id": "INC-2", "device_id": "D2", "start_time": start_time},
    ]
    df_incidents = pd.DataFrame(incidents_data)

    # Create resolutions
    service.create_resolution(Resolution(
        incident_id="INC-1",
        device_id="D1",
        root_cause="A",
        resolution_action="B",
        validation_action="C",
        resolved_by="D",
        resolution_timestamp=start_time + timedelta(minutes=60), # MTTR: 60
        acknowledged_at=start_time + timedelta(minutes=10),      # MTTA: 10
        diagnosed_at=start_time + timedelta(minutes=30),         # MTTD: 20
        resolution_duration=60.0,
        first_time_resolution=True
    ))

    service.create_resolution(Resolution(
        incident_id="INC-2",
        device_id="D2",
        root_cause="A",
        resolution_action="B",
        validation_action="C",
        resolved_by="D",
        resolution_timestamp=start_time + timedelta(minutes=120), # MTTR: 120
        acknowledged_at=start_time + timedelta(minutes=20),       # MTTA: 20
        diagnosed_at=start_time + timedelta(minutes=60),          # MTTD: 40
        resolution_duration=120.0,
        first_time_resolution=False
    ))

    report = service.calculate_kpis(df_incidents)

    assert report.total_incidents == 2
    assert report.mtta_minutes == 15.0   # (10 + 20) / 2
    assert report.mttd_minutes == 30.0   # (20 + 40) / 2
    assert report.mttr_minutes == 90.0   # (60 + 120) / 2
    assert report.ftr_rate == 50.0       # 1 out of 2
