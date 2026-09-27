# Databricks AI/BI Dashboard Specification

This document defines the layout, SQL queries, and KPI calculations for the Network Operations Intelligence Platform (NOIPMP) Databricks AI/BI Dashboard.

All queries strictly target the `noipmp_gold` schema.

---

## Global Dashboard Filters
* `customer_id`
* `location_id`
* `device_id`
* `vendor`
* `model`
* `criticality` (1-5)
* `severity` (Critical, High, Medium, Low)
* `risk_level` (CRITICAL, HIGH, MEDIUM, LOW)
* `date_range` (Start Date, End Date)

---

## Page 1: EXECUTIVE OVERVIEW

### KPIs and Calculation Logic
1. **Total Devices**: Count of all distinct managed devices in the inventory.
2. **Open Incidents**: Count of incidents where `status != 'RESOLVED'`.
3. **MTTA (Mean Time to Acknowledge)**: Average duration between incident `start_time` and `acknowledged_at`.
4. **Mean Time to Diagnose (MTTD)**: Average duration between `acknowledged_at` and `diagnosed_at`.
5. **MTTR (Mean Time to Resolve)**: Average duration between incident `start_time` and `recovery_time`.
6. **First-Time Resolution Rate**: Percentage of resolved incidents where `first_time_resolution = TRUE`.
7. **Predictive Alerts**: Total count of active alerts triggered by the ML pipeline where `risk_level` IN ('HIGH', 'CRITICAL').
8. **Preventive Actions**: Total count of created preventive actions currently tracked.
9. **Incidents Prevented**: Count of preventive actions where `was_prevented = TRUE`.
10. **KB Articles Created**: Total distinct `kb_id`s in the knowledge base.
11. **KB Reuse Rate**: Total `matched_incident_count` / Total Resolved Incidents.

### SQL Queries (Executive)

```sql
-- Executive KPIs Rollup
SELECT 
    (SELECT COUNT(DISTINCT device_id) FROM noipmp_gold.device_inventory) AS Total_Devices,
    (SELECT COUNT(DISTINCT incident_id) FROM noipmp_gold.incident_analytics WHERE status != 'RESOLVED') AS Open_Incidents,
    (SELECT ROUND(AVG(mtta_minutes), 1) FROM noipmp_gold.business_kpis) AS MTTA,
    (SELECT ROUND(AVG(mttd_minutes), 1) FROM noipmp_gold.business_kpis) AS Mean_Time_to_Diagnose,
    (SELECT ROUND(AVG(mttr_minutes), 1) FROM noipmp_gold.business_kpis) AS MTTR,
    (SELECT ROUND(AVG(ftr_rate), 1) FROM noipmp_gold.business_kpis) AS First_Time_Resolution_Rate,
    (SELECT COUNT(*) FROM noipmp_gold.predictive_risk WHERE risk_level IN ('HIGH', 'CRITICAL')) AS Predictive_Alerts,
    (SELECT COUNT(*) FROM noipmp_gold.preventive_actions) AS Preventive_Actions,
    (SELECT COUNT(*) FROM noipmp_gold.preventive_actions WHERE was_prevented = TRUE) AS Incidents_Prevented,
    (SELECT COUNT(DISTINCT kb_id) FROM noipmp_gold.knowledge_metrics) AS KB_Articles_Created,
    (SELECT ROUND(SUM(matched_incident_count) / SUM(reuse_count) * 100, 1) FROM noipmp_gold.knowledge_metrics) AS KB_Reuse_Rate
```

---

## Page 2: OPERATIONS

### SQL Queries (Operations)

```sql
-- Incident Trend Over Time
SELECT DATE(start_time) AS Date, COUNT(incident_id) AS Incidents
FROM noipmp_gold.incident_analytics
GROUP BY DATE(start_time)
ORDER BY Date;

-- Severity Distribution
SELECT severity, COUNT(incident_id) AS Incidents
FROM noipmp_gold.incident_analytics
GROUP BY severity;

-- Top RCA Categories
SELECT probable_rca, COUNT(incident_id) AS Incidents
FROM noipmp_gold.incident_analytics
WHERE probable_rca IS NOT NULL
GROUP BY probable_rca
ORDER BY Incidents DESC;

-- Top Affected Devices
SELECT device_id, COUNT(incident_id) AS Incidents, SUM(duration_minutes) AS Total_Downtime
FROM noipmp_gold.incident_analytics
GROUP BY device_id
ORDER BY Incidents DESC
LIMIT 10;

-- MTTR by RCA Category
SELECT probable_rca, ROUND(AVG(mttr_minutes), 1) AS MTTR
FROM noipmp_gold.incident_analytics
WHERE probable_rca IS NOT NULL
GROUP BY probable_rca
ORDER BY MTTR DESC;

-- Repeat Incidents (Devices with > 1 incident in same category)
SELECT device_id, probable_rca, COUNT(incident_id) AS Incident_Count
FROM noipmp_gold.incident_analytics
GROUP BY device_id, probable_rca
HAVING Incident_Count > 1
ORDER BY Incident_Count DESC;
```

---

## Page 3: PREDICTIVE MAINTENANCE

### SQL Queries (Predictive)

```sql
-- Top 10 High-Risk Devices
SELECT 
    device_id AS Device,
    risk_level AS Risk,
    ROUND(failure_probability * 100, 1) AS Failure_Probability,
    predicted_issue AS Predicted_Issue,
    top_risk_factors AS Top_Risk_Factors,
    recommended_action AS Recommended_Action
FROM noipmp_gold.predictive_risk
WHERE risk_level IN ('HIGH', 'CRITICAL')
ORDER BY failure_probability DESC
LIMIT 10;

-- Risk Trend (Distribution of Risk Levels over time)
SELECT DATE(prediction_timestamp) AS Date, risk_level, COUNT(device_id) AS Device_Count
FROM noipmp_gold.predictive_risk_history
GROUP BY DATE(prediction_timestamp), risk_level
ORDER BY Date;

-- Devices Moving from LOW -> HIGH
SELECT current.device_id
FROM noipmp_gold.predictive_risk current
JOIN noipmp_gold.predictive_risk_history past 
  ON current.device_id = past.device_id
WHERE current.risk_level IN ('HIGH', 'CRITICAL')
  AND past.risk_level = 'LOW'
  AND past.prediction_timestamp = current.prediction_timestamp - INTERVAL 7 DAYS;

-- Devices Requiring Preventive Action
SELECT device_id, action_id, recommended_action, status
FROM noipmp_gold.preventive_actions
WHERE status IN ('RECOMMENDED', 'ACKNOWLEDGED');
```

---

## Page 4: VULNERABILITY & KNOWLEDGE

### SQL Queries (Vulnerability & Knowledge)

```sql
-- CVE Exposure Summary
SELECT 
    SUM(cve_count) AS Total_CVEs,
    SUM(critical_cve_count) AS Critical_CVEs,
    SUM(high_cve_count) AS High_CVEs
FROM noipmp_gold.vulnerability_dashboard;

-- Unpatched Devices & Firmware Age
SELECT 
    device_id, 
    firmware_version, 
    firmware_age_days,
    patch_age_days,
    critical_cve_count,
    recommended_firmware
FROM noipmp_gold.vulnerability_dashboard
WHERE critical_cve_count > 0 OR high_cve_count > 0
ORDER BY critical_cve_count DESC;

-- KB Articles Count & Status
SELECT status, COUNT(kb_id) AS Article_Count
FROM noipmp_gold.knowledge_metrics
GROUP BY status;

-- KB Version & Reuse Table
SELECT 
    kb_id, 
    title, 
    version, 
    status, 
    reuse_count, 
    matched_incident_count
FROM noipmp_gold.knowledge_metrics
ORDER BY reuse_count DESC;
```
