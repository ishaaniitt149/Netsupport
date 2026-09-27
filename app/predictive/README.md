# Predictive Maintenance Module

This module implements a machine learning pipeline to predict network device incidents based on telemetry, incident history, and device metadata.

## Architecture
- **Feature Pipeline**: Computes rolling aggregations over 24h, 7d, 30d periods. To avoid data leakage, all features for timestamp `T` are strictly computed on the `[T - window, T)` interval. The target variable `incident_next_7_days` is computed on the `[T, T + 7 days)` interval.
- **ML Pipeline**: A time-aware `RandomForestClassifier` trained on the generated features. Evaluates metrics such as Precision, Recall, F1, ROC-AUC, PR-AUC, and feature importances.

## Model Limitations
> **IMPORTANT: This model is for prototype and demonstration purposes only. It is NOT production-ready or intended to be highly accurate out-of-the-box.**

- **Prototype Accuracy**: The ML model relies on synthetic data and a simplified feature space. Predictions and risk scores should be treated as illustrative of the platform's capability, not as authoritative engineering foresight.
- **Time-Aware Split**: While temporal leakage is avoided during feature construction and data splitting (e.g. chronological split rather than random train/test split), real-world concept drift requires continuous retraining strategies not fully modeled here.
- **Top Contributing Features**: Local feature contributions are currently simplified as a global-importance scaling, not true SHAP values.
- **Target Definition**: Incidents are broadly classified into a binary 7-day horizon.

## Artifacts
The training pipeline automatically saves:
- `rf_model.joblib`: Serialized RandomForest model
- `metrics.json`: Classification metrics (Precision, Recall, AUCs, CM)
- `features.json`: Ordered list of input feature columns
