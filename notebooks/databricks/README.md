# Databricks Medallion Architecture

This directory contains the Databricks notebooks implementing the Medallion architecture (Bronze, Silver, Gold) for the Network Operations Intelligence Platform (NOIPMP).

## Notebooks

### Data Ingestion & Quality
* **`01_ingest_synthetic_data`**: Ingests raw CSV/Parquet files into `noipmp_bronze` Delta tables.
* **`02_data_quality`**: Validates null constraints and schema constraints before moving to Silver.
* **`03_bronze_to_silver`**: Casts timestamps, removes duplicates, and stages data in `noipmp_silver`.

### Core Application Logic (PySpark)
* **`04_incident_correlation`**: Uses Window functions to track transitions (e.g. `NODE_DOWN` → `NODE_UP`) and calculate downtime.
* **`05_rca_analysis`**: Applies deterministic RCA logic using PySpark Pandas UDFs over diagnostic logs.

### Predictive Maintenance
* **`06_feature_engineering`**: Creates 24h, 7d, 30d rolling windows natively in PySpark (`rangeBetween`). Prevents data leakage by shifting window constraints.
* **`07_model_training`**: Trains ML models (RandomForest) and logs experiments using MLflow.
* **`08_prediction`**: Applies batch inference on the current feature snapshot.
* **`09_vulnerability_enrichment`**: Correlates devices with PSIRT/NVD vulnerability databases.

### Analytics (Gold)
* **`10_kpi_metrics`**: Aggregates resolutions to calculate platform KPIs (MTTA, MTTD, MTTR).
* **`11_gold_tables`**: Computes final dimensional data for PowerBI or Databricks SQL Dashboards (e.g. `device_health`, `vulnerability_dashboard`).

## Design Principles
1. **No Data Leakage**: ML Feature engineering is designed to never peek into the future, utilizing PySpark `rangeBetween` with negative bounds.
2. **Deterministic Processing**: RCA and Correlators use rigorous data structures (UDFs mapped to explicit rules) rather than non-deterministic LLMs.
3. **Appropriate Scaling**: PySpark is used for high-volume logs (telemetry, incidents); Pandas is leveraged for smaller ML operations during model training.
