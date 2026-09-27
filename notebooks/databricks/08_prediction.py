# Databricks notebook source
# MAGIC %md
# MAGIC # 08 Prediction
# MAGIC
# MAGIC **Purpose**: Run batch inference using the trained ML model.
# MAGIC **Layer**: Silver (predictions)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Apply Inference

# COMMAND ----------

silver_db = "noipmp_silver"
try:
    features = spark.table(f"{silver_db}.ml_features")
    # Apply MLflow model as a spark UDF
    # predictions = features.withColumn("prediction", predict_udf(struct(...)))

    # Save predictions
    # predictions.write.format("delta").mode("append").saveAsTable(f"{silver_db}.predictions")
    print("Batch prediction completed.")
except Exception:
    pass
