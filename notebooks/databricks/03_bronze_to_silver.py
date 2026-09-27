# Databricks notebook source
# MAGIC %md
# MAGIC # 03 Bronze to Silver
# MAGIC
# MAGIC **Purpose**: Clean, filter, and cast Bronze data into the Silver layer.
# MAGIC **Layer**: Silver
# MAGIC
# MAGIC We apply schema enforcement, deduplication, and typing.

# COMMAND ----------

from pyspark.sql.functions import col, to_timestamp

bronze_db = "noipmp_bronze"
silver_db = "noipmp_silver"

spark.sql(f"CREATE DATABASE IF NOT EXISTS {silver_db}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Silver Devices

# COMMAND ----------

devices = spark.table(f"{bronze_db}.raw_devices").dropDuplicates(["device_id"])
devices.write.format("delta").mode("overwrite").saveAsTable(f"{silver_db}.devices")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Silver Telemetry

# COMMAND ----------

telemetry = (spark.table(f"{bronze_db}.raw_telemetry")
             .withColumn("timestamp", to_timestamp(col("timestamp")))
             .dropDuplicates(["device_id", "timestamp"]))

telemetry.write.format("delta").mode("overwrite").partitionBy("device_id").saveAsTable(f"{silver_db}.telemetry")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Silver Events

# COMMAND ----------

events = (spark.table(f"{bronze_db}.raw_events")
          .withColumn("timestamp", to_timestamp(col("timestamp")))
          .dropDuplicates(["event_id"]))

events.write.format("delta").mode("overwrite").saveAsTable(f"{silver_db}.events")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Silver Resolutions

# COMMAND ----------

try:
    res = spark.table(f"{bronze_db}.raw_resolutions")
    res.write.format("delta").mode("overwrite").saveAsTable(f"{silver_db}.resolutions")
except Exception:
    print("No resolutions to promote to Silver yet.")
