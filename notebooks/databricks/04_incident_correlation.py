# Databricks notebook source
# MAGIC %md
# MAGIC # 04 Incident Correlation
# MAGIC
# MAGIC **Purpose**: Correlate individual node up/down and packet loss events into stateful Incidents.
# MAGIC **Layer**: Silver (derived)
# MAGIC
# MAGIC Uses PySpark window functions to match down events with subsequent up events to create a duration-based incident.

# COMMAND ----------

from pyspark.sql.functions import col, lead, unix_timestamp
from pyspark.sql.window import Window

silver_db = "noipmp_silver"
events = spark.table(f"{silver_db}.events")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Correlate Events

# COMMAND ----------

# Filter out only the critical transition events
transitions = events.filter(col("event_type").isin("NODE_DOWN", "NODE_UP", "PACKET_LOSS", "RECOVERY"))

windowSpec = Window.partitionBy("device_id").orderBy("timestamp")

# Get the next event for this device
with_next = transitions.withColumn("next_event", lead("event_type").over(windowSpec)) \
                       .withColumn("next_time", lead("timestamp").over(windowSpec))

# Filter down to just the DOWN/PACKET_LOSS events where the next event is a recovery
incidents_df = with_next.filter(
    (col("event_type").isin("NODE_DOWN", "PACKET_LOSS")) &
    (col("next_event").isin("NODE_UP", "RECOVERY"))
).select(
    col("event_id").alias("incident_id"),  # Using start event ID as incident ID
    col("device_id"),
    col("timestamp").alias("start_time"),
    col("next_time").alias("recovery_time"),
    col("event_type").alias("alert_type")
)

# Calculate duration in minutes
incidents_df = incidents_df.withColumn(
    "duration_minutes",
    (unix_timestamp("recovery_time") - unix_timestamp("start_time")) / 60.0
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Save to Silver

# COMMAND ----------

incidents_df.write.format("delta").mode("overwrite").saveAsTable(f"{silver_db}.incidents")
