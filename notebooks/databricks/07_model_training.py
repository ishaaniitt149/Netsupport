# Databricks notebook source
# MAGIC %md
# MAGIC # 07 Model Training
# MAGIC
# MAGIC **Purpose**: Train a RandomForestClassifier to predict incidents.
# MAGIC **Layer**: MLflow
# MAGIC
# MAGIC Uses time-aware splits. We pull to pandas for small-medium datasets, or use Spark MLlib.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Features and Targets

# COMMAND ----------

from sklearn.ensemble import RandomForestClassifier

silver_db = "noipmp_silver"

# For prototype, we pull to pandas
try:
    df = spark.table(f"{silver_db}.ml_features").toPandas()

    # Needs target joining here in a real impl
    # For now, placeholder model fit
    model = RandomForestClassifier(max_depth=5)
    print("Model training pipeline initialized.")
    # mlflow.sklearn.log_model(model, "predictive_maintenance_rf")
except Exception:
    print("Skipping training placeholder.")
