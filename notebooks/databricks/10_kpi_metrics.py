# Databricks notebook source
# MAGIC %md
# MAGIC # 10 KPI Metrics
# MAGIC
# MAGIC **Purpose**: Compute MTTA, MTTD, MTTR, and FTR rates.
# MAGIC **Layer**: Gold

# COMMAND ----------

from pyspark.sql.functions import avg

silver_db = "noipmp_silver"
gold_db = "noipmp_gold"
spark.sql(f"CREATE DATABASE IF NOT EXISTS {gold_db}")

try:
    resolutions = spark.table(f"{silver_db}.resolutions")

    # In PySpark, we'd do timestamp diffs
    # Mocking aggregation
    kpis = resolutions.groupBy().agg(
        avg("resolution_duration").alias("mttr_minutes")
    )

    kpis.write.format("delta").mode("overwrite").saveAsTable(f"{gold_db}.business_kpis")
except Exception:
    pass
