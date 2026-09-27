# Event Schemas Specification

## Project: Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)

---

## 1. Event Ingestion Schemas (SolarWinds & Cisco Ingestion Stream)

### 1.1 `SolarWindsAlertEvent` (Outage / Packet Loss Alert)
Simulates or maps directly from SolarWinds NPM alert email or webhook notification.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SolarWindsAlertEvent",
  "type": "object",
  "properties": {
    "event_id": {"type": "string", "description": "Unique ingestion event UUID"},
    "source_system": {"type": "string", "enum": ["SolarWinds-NPM", "Synthetic-Generator"]},
    "alert_id": {"type": "string", "description": "SolarWinds AlertObjectID"},
    "alert_name": {"type": "string", "example": "Node Down Alert"},
    "severity": {"type": "string", "enum": ["CRITICAL", "MAJOR", "WARNING", "INFO"]},
    "device_hostname": {"type": "string", "example": "nyc-acc-sw01.corp.internal"},
    "device_ip": {"type": "string", "format": "ipv4", "example": "10.240.12.15"},
    "timestamp": {"type": "string", "format": "date-time"},
    "trigger_condition": {
      "type": "string",
      "example": "Packet loss on node nyc-acc-sw01 exceeds 80% for 3 consecutive polls"
    },
    "raw_email_subject": {
      "type": "string",
      "example": "ALERT: Node nyc-acc-sw01.corp.internal is Down"
    },
    "raw_email_body": {"type": "string"},
    "is_synthetic": {"type": "boolean", "default": true}
  },
  "required": [
    "event_id", "source_system", "alert_id", "severity",
    "device_hostname", "device_ip", "timestamp", "is_synthetic"
  ]
}
```

---

### 1.2 `SolarWindsRecoveryEvent` (Node Recovery Notification)
Simulates or maps from the second SolarWinds email indicating recovery.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SolarWindsRecoveryEvent",
  "type": "object",
  "properties": {
    "event_id": {"type": "string", "description": "Unique ingestion event UUID"},
    "source_system": {"type": "string", "enum": ["SolarWinds-NPM", "Synthetic-Generator"]},
    "alert_id": {"type": "string", "description": "Correlated SolarWinds AlertObjectID"},
    "device_hostname": {"type": "string", "example": "nyc-acc-sw01.corp.internal"},
    "device_ip": {"type": "string", "format": "ipv4", "example": "10.240.12.15"},
    "recovery_timestamp": {"type": "string", "format": "date-time"},
    "outage_duration_seconds": {"type": "number", "example": 560.0},
    "raw_email_subject": {
      "type": "string",
      "example": "RECOVERY: Node nyc-acc-sw01.corp.internal is Up"
    },
    "raw_email_body": {"type": "string"},
    "is_synthetic": {"type": "boolean", "default": true}
  },
  "required": [
    "event_id", "source_system", "alert_id", "device_hostname",
    "device_ip", "recovery_timestamp", "is_synthetic"
  ]
}
```

---

### 1.3 `CiscoDiagnosticPayload` (RCA Script Output Stream)
Simulates or captures the SolarWinds post-recovery executed diagnostic CLI dump.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CiscoDiagnosticPayload",
  "type": "object",
  "properties": {
    "payload_id": {"type": "string"},
    "device_hostname": {"type": "string", "example": "nyc-acc-sw01.corp.internal"},
    "device_ip": {"type": "string", "format": "ipv4"},
    "execution_timestamp": {"type": "string", "format": "date-time"},
    "executed_commands": {
      "type": "array",
      "items": {"type": "string"},
      "example": [
        "show version",
        "show interfaces TenGigabitEthernet1/0/1",
        "show interfaces TenGigabitEthernet1/0/1 transceiver detail",
        "show environment power",
        "show processes cpu sorted | exclude 0.00",
        "show logging | include ERROR|CRIT|WARN"
      ]
    },
    "raw_cli_output": {
      "type": "string",
      "description": "Complete verbatim text output stream captured from device terminal"
    },
    "is_synthetic": {"type": "boolean", "default": true}
  },
  "required": [
    "payload_id", "device_hostname", "device_ip",
    "execution_timestamp", "raw_cli_output", "is_synthetic"
  ]
}
```

---

## 2. Internal Domain & Platform Event Schemas

### 2.1 `IncidentCorrelatedEvent`
Emitted by the Correlation Engine when Alert, Recovery, and Diagnostic blocks are successfully united.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "IncidentCorrelatedEvent",
  "type": "object",
  "properties": {
    "incident_id": {"type": "string"},
    "correlation_state": {
      "type": "string",
      "enum": ["PENDING_DIAGNOSTICS", "CORRELATED_COMPLETE", "ORPHAN_DIAGNOSTIC", "UNRECOVERED_ALERT"]
    },
    "device_hostname": {"type": "string"},
    "device_ip": {"type": "string", "format": "ipv4"},
    "alert_timestamp": {"type": "string", "format": "date-time"},
    "recovery_timestamp": {"type": "string", "format": "date-time"},
    "outage_duration_seconds": {"type": "number"},
    "diagnostic_payload_id": {"type": "string"},
    "correlation_duration_ms": {"type": "number"},
    "is_synthetic": {"type": "boolean", "default": true}
  },
  "required": ["incident_id", "correlation_state", "device_hostname", "is_synthetic"]
}
```

---

### 2.2 `RCAGeneratedEvent`
Emitted when the Deterministic Rule Engine (and grounded LLM summarizer) completes evaluation.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RCAGeneratedEvent",
  "type": "object",
  "properties": {
    "rca_id": {"type": "string"},
    "incident_id": {"type": "string"},
    "device_hostname": {"type": "string"},
    "rule_id": {"type": "string", "example": "R1-OPTICAL-DEGRADATION"},
    "probable_cause": {"type": "string"},
    "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "evidence_citations": {
      "type": "array",
      "items": {"type": "string"}
    },
    "recommended_actions": {
      "type": "array",
      "items": {"type": "string"}
    },
    "llm_executive_summary": {"type": "string"},
    "draft_sop_doc_id": {"type": "string"},
    "evaluation_duration_ms": {"type": "number"},
    "is_synthetic": {"type": "boolean", "default": true}
  },
  "required": [
    "rca_id", "incident_id", "rule_id", "probable_cause",
    "confidence_score", "evidence_citations", "is_synthetic"
  ]
}
```

---

### 2.3 `PredictiveRiskAlertEvent`
Emitted by the Predictive Maintenance Engine when a device crosses into High or Critical risk thresholds.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PredictiveRiskAlertEvent",
  "type": "object",
  "properties": {
    "risk_alert_id": {"type": "string"},
    "device_id": {"type": "string"},
    "device_hostname": {"type": "string"},
    "site_code": {"type": "string"},
    "risk_score": {"type": "number", "minimum": 0.0, "maximum": 100.0},
    "risk_category": {"type": "string", "enum": ["HIGH", "CRITICAL"]},
    "failure_probability_14d": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "leading_risk_factors": {
      "type": "array",
      "items": {"type": "string"}
    },
    "recommended_preventive_action": {"type": "string"},
    "evaluated_at": {"type": "string", "format": "date-time"},
    "is_synthetic": {"type": "boolean", "default": true}
  },
  "required": [
    "risk_alert_id", "device_id", "device_hostname",
    "risk_score", "risk_category", "is_synthetic"
  ]
}
```

---

### 2.4 `PreventiveTicketEvent`
Emitted when a proactive work order is scheduled to service a degrading device before failure occurs.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PreventiveTicketEvent",
  "type": "object",
  "properties": {
    "ticket_id": {"type": "string", "example": "PRV-20260927-0019"},
    "device_id": {"type": "string"},
    "device_hostname": {"type": "string"},
    "risk_score": {"type": "number"},
    "preventive_action_type": {
      "type": "string",
      "enum": ["TRANSCEIVER_REPLACEMENT", "PSU_REPLACEMENT", "FIRMWARE_UPGRADE", "CABLING_AUDIT"]
    },
    "target_completion_date": {"type": "string", "format": "date-time"},
    "assigned_group": {"type": "string", "example": "Network Engineering L3"},
    "status": {"type": "string", "enum": ["OPEN", "SCHEDULED", "COMPLETED", "CANCELLED"]},
    "is_synthetic": {"type": "boolean", "default": true}
  },
  "required": [
    "ticket_id", "device_id", "device_hostname",
    "preventive_action_type", "status", "is_synthetic"
  ]
}
```
