"""Risk explanation service for predictive maintenance."""

import pandas as pd
from pydantic import BaseModel

from app.predictive.ml_pipeline import ModelPrediction, RiskLevel


class RiskExplanation(BaseModel):
    """Explanation for a device's high risk status."""

    device_id: str
    risk_score: float
    failure_probability: float
    top_risk_factors: list[str]
    recommended_preventive_action: str


class RiskExplainer:
    """Explains predictive maintenance risk scores with concrete evidence."""

    def __init__(self):
        # Mapping feature names to human-readable explanation templates
        self.feature_templates = {
            "packet_loss_mean_24h": "Packet loss averaged {value:.2f}% over the last 24 hours",
            "packet_loss_max_24h": "Peak packet loss reached {value:.2f}% in the last 24 hours",
            "packet_loss_trend_24h": "Packet loss trend is increasing at {value:.4f} per hour",
            "packet_loss_mean_7d": "Packet loss averaged {value:.2f}% over the last 7 days",
            "crc_errors_sum_24h": "{value:.0f} CRC errors observed in the last 24 hours",
            "crc_errors_trend_24h": "CRC errors are trending upward at {value:.4f} errors per hour",
            "interface_flaps_sum_24h": "{value:.0f} interface flaps in the last 24 hours",
            "incident_count_7d": "{value:.0f} incidents occurred in the last 7 days",
            "incident_count_30d": "{value:.0f} incidents occurred in the last 30 days",
            "downtime_7d": "{value:.1f} minutes of downtime in the last 7 days",
            "downtime_30d": "{value:.1f} minutes of downtime in the last 30 days",
            "cpu_mean_24h": "CPU utilization averaged {value:.2f}% over the last 24 hours",
            "cpu_max_24h": "Peak CPU utilization reached {value:.2f}% in the last 24 hours",
            "memory_mean_24h": "Memory utilization averaged {value:.2f}% over the last 24 hours",
            "memory_max_24h": "Peak memory utilization reached {value:.2f}% in the last 24 hours",
            "latency_mean_24h": "Latency averaged {value:.2f}ms over the last 24 hours",
            "latency_trend_24h": "Latency is increasing at {value:.4f}ms per hour",
            "firmware_age_days": "Firmware is {value:.0f} days old",
            "patch_age_days": "Device has been vulnerable to known CVEs for {value:.0f} days",
            "cve_count": "Device is exposed to {value:.0f} known vulnerabilities",
            "critical_cve_count": "Device has {value:.0f} CRITICAL vulnerabilities",
            "device_criticality": "Device criticality level is {value:.0f}",
        }

    def explain(
        self,
        prediction: ModelPrediction,
        feature_row: pd.Series
    ) -> RiskExplanation | None:
        """
        Generates an explanation for HIGH or CRITICAL risk predictions.
        Returns None for LOW or MEDIUM risk predictions.
        """
        if prediction.risk_level not in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return None

        risk_factors = []
        for feature_name, importance in prediction.top_contributing_features.items():
            if feature_name in feature_row.index:
                value = feature_row[feature_name]

                # Only explain features if they actually contributed to risk (e.g. non-zero value)
                # Some features (like trend) could be negative; assume positive values for risk in this simplified logic.
                if pd.notna(value) and value > 0:
                    template = self.feature_templates.get(feature_name, f"{feature_name} is {{value}}")
                    risk_factors.append(template.format(value=value))

        # Generate preventive action based on the top contributing feature
        primary_feature = next(iter(prediction.top_contributing_features.keys()), "")

        action = "Schedule general maintenance window."
        if "packet_loss" in primary_feature or "crc_errors" in primary_feature or "flaps" in primary_feature:
            action = "Inspect physical interfaces, optical levels, and cabling. Consider replacing SFP module."
        elif "cve" in primary_feature or "patch_age" in primary_feature or "firmware" in primary_feature:
            action = "Plan and execute firmware upgrade to patch known vulnerabilities."
        elif "cpu" in primary_feature or "memory" in primary_feature:
            action = "Investigate control plane processes and routing tables for resource exhaustion."
        elif "incident" in primary_feature or "downtime" in primary_feature:
            action = "Review recent RCA reports. Recurring incidents suggest incomplete previous resolutions."

        return RiskExplanation(
            device_id=prediction.device_id,
            risk_score=prediction.risk_score,
            failure_probability=prediction.failure_probability,
            top_risk_factors=risk_factors,
            recommended_preventive_action=action,
        )
