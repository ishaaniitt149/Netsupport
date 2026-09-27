# Databricks notebook source
# MAGIC %md
# MAGIC # 02 Data Quality Checks
# MAGIC
# MAGIC **Purpose**: Validate schema and basic quality of the Bronze layer data.
# MAGIC **Layer**: Bronze to Silver transition
# MAGIC
# MAGIC Uses PySpark to perform null checks and constraint validation before promoting to Silver.

# COMMAND ----------

from pyspark.sql.functions import col, when
from pyspark.sql.functions import sum as _sum

bronze_db = "noipmp_bronze"

# COMMAND ----------
# MAGIC %md
# MAGIC ## Check Telemetry Quality

# COMMAND ----------

telemetry = spark.table(f"{bronze_db}.raw_telemetry")

# Assert no null timestamps or device_ids
null_counts = telemetry.select([
    _sum(when(col(c).isNull(), 1).otherwise(0)).alias(c)
    for c in ["timestamp", "device_id"]
]).collect()[0]

assert null_counts["timestamp"] == 0, "Null timestamps found in telemetry"
assert null_counts["device_id"] == 0, "Null device_ids found in telemetry"

print("Telemetry quality check passed.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Check Events Quality

# COMMAND ----------

events = spark.table(f"{bronze_db}.raw_events")

# Assert events have valid types
valid_events = events.filter(col("event_type").isin("NODE_DOWN", "NODE_UP", "PACKET_LOSS", "RECOVERY")).count()
total_events = events.count()

assert valid_events == total_events, f"Found invalid event types. Valid: {valid_events}, Total: {total_events}"

print("Events quality check passed.")
