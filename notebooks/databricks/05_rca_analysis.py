# Databricks notebook source
# MAGIC %md
# MAGIC # 05 RCA Analysis
# MAGIC
# MAGIC **Purpose**: Apply deterministic rule-based RCA on incidents using diagnostic data.
# MAGIC **Layer**: Silver (derived)
# MAGIC
# MAGIC In this Databricks notebook, we apply a Pandas UDF (Vectorized UDF) to apply
# MAGIC Python-based regex parsing and rule execution over large datasets of raw CLI output.

# COMMAND ----------

import json

import pandas as pd
from pyspark.sql.functions import col, pandas_udf

# This would typically import from the wheel installed on the cluster
# For the prototype script, we mock the UDF behavior

@pandas_udf("string")
def apply_deterministic_rca(rca_text: pd.Series) -> pd.Series:
    """
    Mock Pandas UDF applying the DeterministicRCAEngine logic.
    Returns JSON serialized RCA result.
    """
    results = []
    for text in rca_text:
        # Mock logic based on text content
        if pd.isna(text):
            results.append("{}")
        elif "CRC" in text:
            results.append(json.dumps({"probable_rca": "Interface degradation", "confidence": 0.88}))
        elif "CPU" in text:
            results.append(json.dumps({"probable_rca": "High CPU", "confidence": 0.95}))
        else:
            results.append(json.dumps({"probable_rca": "Unknown", "confidence": 0.0}))
    return pd.Series(results)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Apply RCA Rules

# COMMAND ----------

bronze_db = "noipmp_bronze"
silver_db = "noipmp_silver"

try:
    rca = spark.table(f"{bronze_db}.raw_rca")
    rca = rca.withColumn("rca_result_json", apply_deterministic_rca(col("raw_output")))
    rca.write.format("delta").mode("overwrite").saveAsTable(f"{silver_db}.diagnostics")
except Exception as e:
    print(f"Skipping RCA processing: {e}")
