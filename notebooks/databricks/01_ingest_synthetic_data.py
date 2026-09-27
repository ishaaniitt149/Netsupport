# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Ingest Synthetic Data
# MAGIC
# MAGIC **Purpose**: Ingest raw synthetic CSV/JSONL files into Bronze delta tables.
# MAGIC **Layer**: Bronze
# MAGIC
# MAGIC This notebook mimics the batch landing zone where synthetic telemetry, events,
# MAGIC and device inventories arrive and are appended into immutable Bronze tables.

# COMMAND ----------

from pyspark.sql.types import *

# Define path configurations
raw_base_path = "file:/workspace/data/synthetic"
bronze_db = "noipmp_bronze"

spark.sql(f"CREATE DATABASE IF NOT EXISTS {bronze_db}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Ingest Devices

# COMMAND ----------

# raw_devices schema
devices_df = (spark.read.format("csv")
              .option("header", "true")
              .option("inferSchema", "true")
              .load(f"{raw_base_path}/inventory.csv"))

devices_df.write.format("delta").mode("overwrite").saveAsTable(f"{bronze_db}.raw_devices")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Ingest Telemetry

# COMMAND ----------

telemetry_df = (spark.read.format("parquet")
                .load(f"{raw_base_path}/telemetry.parquet"))

telemetry_df.write.format("delta").mode("overwrite").saveAsTable(f"{bronze_db}.raw_telemetry")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Ingest Events

# COMMAND ----------

events_df = (spark.read.format("csv")
             .option("header", "true")
             .option("inferSchema", "true")
             .load(f"{raw_base_path}/solarwinds_events.csv"))

events_df.write.format("delta").mode("overwrite").saveAsTable(f"{bronze_db}.raw_events")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Ingest RCA & Resolutions

# COMMAND ----------

# Since RCA emails are raw text and metadata, we mock the ingestion of the metadata here.
# In a real pipeline, Auto Loader would ingest raw text into a delta table.
try:
    rca_meta = spark.read.format("csv").option("header", "true").load(f"{raw_base_path}/rca_emails/metadata.csv")
    rca_meta.write.format("delta").mode("overwrite").saveAsTable(f"{bronze_db}.raw_rca")
except Exception as e:
    print(f"Skipping raw_rca ingestion: {e}")

try:
    # Assuming resolutions are written out somewhere or we use processed ones for the mock
    resolutions_df = spark.read.format("parquet").load("file:/workspace/data/processed/resolutions.parquet")
    resolutions_df.write.format("delta").mode("overwrite").saveAsTable(f"{bronze_db}.raw_resolutions")
except Exception as e:
    print(f"Skipping raw_resolutions ingestion: {e}")
