"""Tests for ML pipeline."""

from datetime import timedelta
from pathlib import Path

import pandas as pd

from app.predictive.ml_pipeline import MLPipeline, RiskLevel


def test_ml_pipeline(tmp_path: Path):
    pipeline = MLPipeline(artifact_dir=tmp_path)

    # Generate mock feature data
    base_time = pd.to_datetime("2023-01-01 00:00:00")

    times = []
    device_ids = []
    f1 = []
    f2 = []
    target = []

    for i in range(100):
        t = base_time + timedelta(hours=i)
        times.append(t)
        device_ids.append("DEV-1")
        # Generate some synthetic separation
        if i % 5 == 0:
            f1.append(10.0)
            f2.append(50.0)
            target.append(1)
        else:
            f1.append(0.1)
            f2.append(0.5)
            target.append(0)

    df = pd.DataFrame({
        "timestamp": times,
        "device_id": device_ids,
        "packet_loss_mean_24h": f1,
        "crc_errors_sum_24h": f2,
        "incident_next_7_days": target
    })

    feature_cols = ["packet_loss_mean_24h", "crc_errors_sum_24h"]

    # Train
    metrics = pipeline.train_and_evaluate(df, feature_cols, "incident_next_7_days")

    assert metrics is not None
    assert "precision" in metrics
    assert "roc_auc" in metrics
    assert "feature_importance" in metrics

    assert (tmp_path / "rf_model.joblib").exists()
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "features.json").exists()

    # Inference
    new_data = pd.DataFrame({
        "timestamp": [base_time + timedelta(hours=101), base_time + timedelta(hours=102)],
        "device_id": ["DEV-1", "DEV-2"],
        "packet_loss_mean_24h": [10.0, 0.1],
        "crc_errors_sum_24h": [50.0, 0.5],
    })

    predictions = pipeline.predict(new_data)

    assert len(predictions) == 2
    assert predictions[0].device_id == "DEV-1"
    assert predictions[0].risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert "packet_loss_mean_24h" in predictions[0].top_contributing_features
