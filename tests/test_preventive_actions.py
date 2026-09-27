"""Tests for preventive actions module."""

from datetime import UTC, datetime

import pandas as pd

from app.predictive.ml_pipeline import ModelPrediction, RiskLevel
from app.predictive.preventive_actions import PreventiveActionService, PreventiveActionStatus


def test_generates_action_above_threshold():
    service = PreventiveActionService(risk_threshold=0.75)

    pred = ModelPrediction(
        device_id="DEV-01",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.85,
        risk_score=85.0,
        risk_level=RiskLevel.CRITICAL,
        top_contributing_features={
            "crc_errors_sum_24h": 0.4,
            "packet_loss_mean_24h": 0.3
        }
    )

    row = pd.Series({
        "crc_errors_sum_24h": 1450.0,
        "packet_loss_mean_24h": 5.4,
    })

    action = service.generate_from_prediction(pred, row)

    assert action is not None
    assert action.device_id == "DEV-01"
    assert action.status == PreventiveActionStatus.RECOMMENDED
    assert "1450 CRC errors" in action.reason
    assert "Packet loss" in action.reason


def test_skips_action_below_threshold():
    service = PreventiveActionService(risk_threshold=0.75)

    pred = ModelPrediction(
        device_id="DEV-02",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.60,
        risk_score=60.0,
        risk_level=RiskLevel.HIGH,
        top_contributing_features={
            "crc_errors_sum_24h": 0.4
        }
    )

    row = pd.Series({
        "crc_errors_sum_24h": 1450.0,
    })

    action = service.generate_from_prediction(pred, row)

    assert action is None


def test_update_status():
    service = PreventiveActionService(risk_threshold=0.75)

    pred = ModelPrediction(
        device_id="DEV-01",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.85,
        risk_score=85.0,
        risk_level=RiskLevel.CRITICAL,
        top_contributing_features={"crc_errors_sum_24h": 0.4}
    )

    row = pd.Series({"crc_errors_sum_24h": 1450.0})

    action = service.generate_from_prediction(pred, row)
    assert action.status == PreventiveActionStatus.RECOMMENDED

    updated = service.update_status(action.action_id, PreventiveActionStatus.IN_PROGRESS)
    assert updated.status == PreventiveActionStatus.IN_PROGRESS


def test_evaluate_prevention_success():
    service = PreventiveActionService(risk_threshold=0.75)

    # 1. Action that IS successful
    pred1 = ModelPrediction(
        device_id="DEV-01",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.85,
        risk_score=85.0,
        risk_level=RiskLevel.CRITICAL,
        top_contributing_features={"crc_errors_sum_24h": 0.4}
    )

    row1 = pd.Series({"crc_errors_sum_24h": 1450.0})
    action1 = service.generate_from_prediction(pred1, row1)

    # Complete the action early
    service.update_status(action1.action_id, PreventiveActionStatus.COMPLETED)
    # Manually backdate completion for test
    action1 = service.get_action(action1.action_id)
    action1.updated_at = datetime(2023, 1, 2, tzinfo=UTC)

    # No incidents for this device in the 7 day window
    incidents = [
        {"device_id": "DEV-99", "start_time": "2023-01-03T00:00:00Z"}
    ]

    success = service.evaluate_prevention_success(action1.action_id, incidents)
    assert success is True
    assert action1.was_prevented is True


    # 2. Action that is NOT successful (incident happened anyway)
    pred2 = ModelPrediction(
        device_id="DEV-02",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.85,
        risk_score=85.0,
        risk_level=RiskLevel.CRITICAL,
        top_contributing_features={"crc_errors_sum_24h": 0.4}
    )

    row2 = pd.Series({"crc_errors_sum_24h": 1450.0})
    action2 = service.generate_from_prediction(pred2, row2)
    service.update_status(action2.action_id, PreventiveActionStatus.COMPLETED)
    action2.updated_at = datetime(2023, 1, 2, tzinfo=UTC)

    # Incident occurs on day 3
    incidents2 = [
        {"device_id": "DEV-02", "start_time": "2023-01-03T00:00:00Z"}
    ]

    success2 = service.evaluate_prevention_success(action2.action_id, incidents2)
    assert success2 is False
    assert action2.was_prevented is False


    # 3. Action that was NEVER completed
    pred3 = ModelPrediction(
        device_id="DEV-03",
        prediction_timestamp="2023-01-01T00:00:00Z",
        failure_probability=0.85,
        risk_score=85.0,
        risk_level=RiskLevel.CRITICAL,
        top_contributing_features={"crc_errors_sum_24h": 0.4}
    )

    row3 = pd.Series({"crc_errors_sum_24h": 1450.0})
    action3 = service.generate_from_prediction(pred3, row3)

    success3 = service.evaluate_prevention_success(action3.action_id, [])
    assert success3 is False
    assert action3.was_prevented is False
