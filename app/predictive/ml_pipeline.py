"""Predictive maintenance ML pipeline."""

import json
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

try:
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        average_precision_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
except ImportError:
    pass


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ModelPrediction(BaseModel):
    """Output from the predictive model."""

    device_id: str
    prediction_timestamp: str
    failure_probability: float
    risk_score: float
    risk_level: RiskLevel
    prediction_horizon: str = "7 days"
    top_contributing_features: dict[str, float]


class MLPipeline:
    """Predictive maintenance ML pipeline."""

    def __init__(self, artifact_dir: Path):
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.features = []

    def time_aware_split(self, df: pd.DataFrame, target_col: str, test_ratio: float = 0.2):
        """
        Time-aware train/test split.
        Do NOT use random train_test_split to prevent temporal leakage.
        """
        df = df.sort_values(by="timestamp").copy()

        split_idx = int(len(df) * (1 - test_ratio))

        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]

        return train_df, test_df

    def train_and_evaluate(self, df: pd.DataFrame, feature_cols: list[str], target_col: str) -> dict[str, Any]:
        """Trains the model and evaluates it using time-aware splitting."""

        # Keep features mapping
        self.features = feature_cols

        train_df, test_df = self.time_aware_split(df, target_col)

        X_train = train_df[feature_cols].fillna(0)
        y_train = train_df[target_col]

        X_test = test_df[feature_cols].fillna(0)
        y_test = test_df[target_col]

        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight="balanced",
            random_state=42
        )
        self.model.fit(X_train, y_train)

        # Predictions
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]

        # Metrics
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

        metrics = {
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else 0.0,
            "pr_auc": float(average_precision_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else 0.0,
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
            "true_negatives": int(tn),
        }

        # Feature Importance
        importances = self.model.feature_importances_
        feature_importance = {f: float(imp) for f, imp in zip(feature_cols, importances)}

        metrics["feature_importance"] = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

        # Save artifacts
        self.save_artifacts(metrics)

        return metrics

    def save_artifacts(self, metrics: dict[str, Any]):
        """Saves model and metrics to disk."""
        if self.model is None:
            return

        joblib.dump(self.model, self.artifact_dir / "rf_model.joblib")

        with open(self.artifact_dir / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)

        with open(self.artifact_dir / "features.json", "w") as f:
            json.dump(self.features, f, indent=2)

    def load_artifacts(self):
        """Loads model and features from disk."""
        model_path = self.artifact_dir / "rf_model.joblib"
        feat_path = self.artifact_dir / "features.json"

        if model_path.exists() and feat_path.exists():
            self.model = joblib.load(model_path)
            with open(feat_path) as f:
                self.features = json.load(f)

    def _determine_risk_level(self, prob: float) -> RiskLevel:
        if prob < 0.25:
            return RiskLevel.LOW
        elif prob < 0.50:
            return RiskLevel.MEDIUM
        elif prob < 0.75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def predict(self, df: pd.DataFrame) -> list[ModelPrediction]:
        """Inference on new data."""
        if self.model is None:
            self.load_artifacts()
            if self.model is None:
                raise ValueError("Model not trained or artifacts missing.")

        # Ensure only the features used during training are used for prediction
        X = df[self.features].fillna(0)

        probs = self.model.predict_proba(X)[:, 1]

        importances = self.model.feature_importances_

        predictions = []
        for i, (_, row) in enumerate(df.iterrows()):
            prob = float(probs[i])

            # Top contributing features for this prediction
            # For simplicity, we just return global importances scaled by the feature value
            local_importance = {f: float(row[f] * imp) for f, imp in zip(self.features, importances)}
            top_features = dict(sorted(local_importance.items(), key=lambda x: x[1], reverse=True)[:5])

            predictions.append(
                ModelPrediction(
                    device_id=str(row["device_id"]),
                    prediction_timestamp=str(row["timestamp"]),
                    failure_probability=prob,
                    risk_score=prob * 100,
                    risk_level=self._determine_risk_level(prob),
                    top_contributing_features=top_features
                )
            )

        return predictions
