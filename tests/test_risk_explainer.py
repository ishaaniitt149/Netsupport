"""Tests for predictive risk explainer."""

import pandas as pd

from app.predictive.ml_pipeline import ModelPrediction, RiskLevel
from app.predictive.risk_explainer import RiskExplainer


def test_explains_high_risk_prediction():
    explainer = RiskExplainer()

    pred = ModelPrediction(
        device_id="DEV-01",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.85,
        risk_score=85.0,
        risk_level=RiskLevel.CRITICAL,
        top_contributing_features={
            "crc_errors_sum_24h": 0.4,
            "packet_loss_mean_24h": 0.3,
            "cve_count": 0.2
        }
    )

    # Feature values backing the prediction
    row = pd.Series({
        "device_id": "DEV-01",
        "crc_errors_sum_24h": 1450.0,
        "packet_loss_mean_24h": 5.4,
        "cve_count": 3.0,
        "cpu_mean_24h": 20.0  # Not in top features, shouldn't be explained
    })

    explanation = explainer.explain(pred, row)

    assert explanation is not None
    assert explanation.device_id == "DEV-01"
    assert len(explanation.top_risk_factors) == 3

    # Check that actual values are templated into the strings
    assert "1450 CRC errors observed" in explanation.top_risk_factors[0]
    assert "Packet loss averaged 5.40%" in explanation.top_risk_factors[1]
    assert "exposed to 3 known vulnerabilities" in explanation.top_risk_factors[2]

    # Check preventive action derived from top feature (crc_errors)
    assert "Inspect physical interfaces" in explanation.recommended_preventive_action


def test_skips_low_risk_prediction():
    explainer = RiskExplainer()

    pred = ModelPrediction(
        device_id="DEV-02",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.10,
        risk_score=10.0,
        risk_level=RiskLevel.LOW,
        top_contributing_features={
            "cpu_mean_24h": 0.1
        }
    )

    row = pd.Series({"cpu_mean_24h": 40.0})

    explanation = explainer.explain(pred, row)

    assert explanation is None


def test_ignores_zero_value_features():
    explainer = RiskExplainer()

    pred = ModelPrediction(
        device_id="DEV-03",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.80,
        risk_score=80.0,
        risk_level=RiskLevel.HIGH,
        top_contributing_features={
            "packet_loss_mean_24h": 0.5,
            "crc_errors_sum_24h": 0.3
        }
    )

    # The feature was important globally, but for this specific device it's zero
    row = pd.Series({
        "packet_loss_mean_24h": 5.0,
        "crc_errors_sum_24h": 0.0
    })

    explanation = explainer.explain(pred, row)

    assert explanation is not None
    assert len(explanation.top_risk_factors) == 1
    assert "Packet loss averaged" in explanation.top_risk_factors[0]
