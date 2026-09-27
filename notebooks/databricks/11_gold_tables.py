# Databricks notebook source
# MAGIC %md
# MAGIC # 11 Gold Tables
# MAGIC
# MAGIC **Purpose**: Final aggregations and reporting tables for dashboards.
# MAGIC **Layer**: Gold

# COMMAND ----------

silver_db = "noipmp_silver"
gold_db = "noipmp_gold"

try:
    # Example: Device Health Rollup
    incidents = spark.table(f"{silver_db}.incidents")
    device_health = incidents.groupBy("device_id").count()
    device_health.write.format("delta").mode("overwrite").saveAsTable(f"{gold_db}.device_health")
except Exception:
    pass
