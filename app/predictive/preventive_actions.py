"""Preventive action recommendation module."""

import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.predictive.ml_pipeline import ModelPrediction
from app.predictive.risk_explainer import RiskExplainer


class PreventiveActionStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"


class PreventiveAction(BaseModel):
    """A recommended preventive action based on predictive risk."""

    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str
    prediction_timestamp: datetime
    failure_probability: float
    risk_score: float

    # Textual explanations
    reason: str
    recommended_action: str

    status: PreventiveActionStatus = PreventiveActionStatus.RECOMMENDED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Tracking for evaluation
    prediction_horizon_days: int = 7
    was_prevented: bool | None = None  # None until evaluated


class PreventiveActionService:
    """Manages generation and lifecycle of preventive actions."""

    def __init__(self, risk_threshold: float = 0.75):
        self.risk_threshold = risk_threshold
        self.explainer = RiskExplainer()
        self._actions: dict[str, PreventiveAction] = {}

    def generate_from_prediction(
        self,
        prediction: ModelPrediction,
        feature_row: dict
    ) -> PreventiveAction | None:
        """Creates a preventive action if risk exceeds threshold."""

        if prediction.failure_probability < self.risk_threshold:
            return None

        # Explainer only explains HIGH/CRITICAL (usually > 0.50), threshold here is 0.75 by default
        explanation = self.explainer.explain(prediction, feature_row)
        if not explanation:
            return None

        reason = "\n".join([f"- {factor}" for factor in explanation.top_risk_factors])

        action = PreventiveAction(
            device_id=prediction.device_id,
            prediction_timestamp=datetime.fromisoformat(prediction.prediction_timestamp.replace("Z", "+00:00")),
            failure_probability=prediction.failure_probability,
            risk_score=prediction.risk_score,
            reason=reason,
            recommended_action=explanation.recommended_preventive_action,
        )

        self._actions[action.action_id] = action
        return action

    def get_action(self, action_id: str) -> PreventiveAction | None:
        return self._actions.get(action_id)

    def get_actions_for_device(self, device_id: str) -> list[PreventiveAction]:
        return [a for a in self._actions.values() if a.device_id == device_id]

    def update_status(self, action_id: str, status: PreventiveActionStatus) -> PreventiveAction | None:
        """Update the lifecycle state of the action."""
        action = self.get_action(action_id)
        if not action:
            return None

        action.status = status
        action.updated_at = datetime.now(UTC)
        self._actions[action_id] = action
        return action

    def evaluate_prevention_success(
        self,
        action_id: str,
        actual_incidents: list[dict]
    ) -> bool | None:
        """
        Evaluate if an incident was genuinely prevented.
        
        An incident is ONLY considered prevented if:
        1. The preventive action was explicitly marked COMPLETED.
        2. The completion time was BEFORE the predicted incident window ended.
        3. NO incident occurred in the predicted window.
        """
        action = self.get_action(action_id)
        if not action:
            return None

        if action.status != PreventiveActionStatus.COMPLETED:
            action.was_prevented = False
            self._actions[action_id] = action
            return False

        # Define the risk window
        window_start = action.prediction_timestamp
        import pandas as pd
        window_end = window_start + pd.Timedelta(days=action.prediction_horizon_days)

        # If action completed after window, it was too late to be preventive for this window
        if action.updated_at > window_end:
            action.was_prevented = False
            self._actions[action_id] = action
            return False

        # Check if any incident actually happened in that window
        incident_occurred = False
        for inc in actual_incidents:
            if inc["device_id"] == action.device_id:
                inc_start = inc["start_time"]
                if isinstance(inc_start, str):
                    inc_start = datetime.fromisoformat(inc_start.replace("Z", "+00:00"))

                if window_start <= inc_start < window_end:
                    incident_occurred = True
                    break

        # Successfully prevented if NO incident occurred
        action.was_prevented = not incident_occurred
        self._actions[action_id] = action

        return action.was_prevented
