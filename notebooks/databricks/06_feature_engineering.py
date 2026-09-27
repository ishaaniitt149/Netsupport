# Databricks notebook source
# MAGIC %md
# MAGIC # 06 Feature Engineering
# MAGIC
# MAGIC **Purpose**: Compute rolling time-window features (24h, 7d, 30d) for ML model.
# MAGIC **Layer**: Silver (feature store)
# MAGIC
# MAGIC Prevents data leakage by ensuring calculations for timestamp T only look at [T-window, T).

# COMMAND ----------

from pyspark.sql import Window
from pyspark.sql.functions import avg, col
from pyspark.sql.functions import sum as _sum

silver_db = "noipmp_silver"
telemetry = spark.table(f"{silver_db}.telemetry")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Construct Time Windows

# COMMAND ----------

# Convert time window definitions to seconds for PySpark rangeBetween
w_24h = Window.partitionBy("device_id").orderBy(col("timestamp").cast("long")).rangeBetween(-24*3600, -1)

# Using lag to ensure we look *strictly* before current row timestamp in case of same-second duplicates
features = telemetry.withColumn("packet_loss_mean_24h", avg("packet_loss_percent").over(w_24h)) \
                    .withColumn("crc_errors_sum_24h", _sum("crc_errors").over(w_24h)) \
                    .withColumn("interface_flaps_sum_24h", _sum("interface_flaps").over(w_24h)) \
                    .withColumn("cpu_mean_24h", avg("cpu_utilization").over(w_24h))

features.write.format("delta").mode("overwrite").saveAsTable(f"{silver_db}.ml_features")
