"""Tests for the feature pipeline."""

from datetime import timedelta

import pandas as pd

from app.predictive.feature_pipeline import FeaturePipeline


def test_feature_pipeline_no_leakage():
    # Setup data
    base_time = pd.to_datetime("2023-01-01 00:00:00")

    # 1. Telemetry
    times = [base_time + timedelta(hours=i) for i in range(100)]
    telemetry_data = {
        "timestamp": times,
        "device_id": ["DEV-1"] * 100,
        "packet_loss_percent": [i % 5 for i in range(100)],
        "crc_errors": [1 if i % 10 == 0 else 0 for i in range(100)],
        "interface_flaps": [0] * 100,
        "cpu_utilization": [50.0] * 100,
        "memory_utilization": [60.0] * 100,
        "latency_ms": [20.0] * 100,
    }
    telemetry_df = pd.DataFrame(telemetry_data)

    # 2. Incidents
    # Incident starts at hour 50, duration 2 hours
    incidents_data = {
        "device_id": ["DEV-1"],
        "start_time": [base_time + timedelta(hours=50)],
        "recovery_time": [base_time + timedelta(hours=52)],
        "duration_minutes": [120.0]
    }
    incidents_df = pd.DataFrame(incidents_data)

    # 3. Meta
    meta_data = {
        "device_id": ["DEV-1"],
        "firmware_age_days": [100],
        "patch_age_days": [30],
        "cve_count": [2],
        "critical_cve_count": [1],
        "device_criticality": [5],
    }
    meta_df = pd.DataFrame(meta_data)

    # Create features
    pipeline = FeaturePipeline(telemetry_df, incidents_df, meta_df)
    features = pipeline.create_features()

    assert not features.empty

    # Check data leakage in target
    # Time T = 49: the incident starts at 50, so in the next 7 days there is an incident
    t_49 = features[features["timestamp"] == base_time + timedelta(hours=49)].iloc[0]
    assert t_49["incident_next_7_days"] == 1

    # Check data leakage in features
    # Time T = 50: The incident starts AT 50. Features for T=50 must ONLY use data < 50.
    # So incident_count_7d should be 0 because the incident hasn't started strictly before T=50.
    t_50 = features[features["timestamp"] == base_time + timedelta(hours=50)].iloc[0]
    assert t_50["incident_count_7d"] == 0
    assert t_50["incident_next_7_days"] == 1

    # Time T = 51: The incident started at 50. So it is in the past now.
    t_51 = features[features["timestamp"] == base_time + timedelta(hours=51)].iloc[0]
    assert t_51["incident_count_7d"] == 1

    # Telemetry test
    # T = 1. Window 24h before T=1 is just T=0.
    t_1 = features[features["timestamp"] == base_time + timedelta(hours=1)].iloc[0]
    assert t_1["packet_loss_mean_24h"] == 0.0  # value at T=0

    # Metadata included
    assert t_50["cve_count"] == 2
    assert t_50["device_criticality"] == 5
