# API Contracts & Interface Specifications

## Project: Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)

---

## 1. Internal Python Protocol Contracts (Hexagonal Boundary)

### 1.1 Ingestion Port Protocol (`EventIngestionPort`)
```python
from typing import Protocol, Iterator
from .schemas import SolarWindsAlertEvent, SolarWindsRecoveryEvent, CiscoDiagnosticPayload


class EventIngestionPort(Protocol):
    def poll_alerts(self, batch_size: int = 50) -> Iterator[SolarWindsAlertEvent]:
        """Poll or receive incoming SolarWinds alert events."""
        ...

    def poll_recoveries(self, batch_size: int = 50) -> Iterator[SolarWindsRecoveryEvent]:
        """Poll or receive incoming SolarWinds recovery events."""
        ...

    def poll_diagnostics(self, batch_size: int = 50) -> Iterator[CiscoDiagnosticPayload]:
        """Poll or receive executed Cisco CLI diagnostic payloads."""
        ...
```

### 1.2 LLM Provider Port Protocol (`LLMProviderPort`)
```python
from typing import Protocol, Optional
from .schemas import Incident, CiscoDiagnosticReport, RCAResult, KBSOPArticle


class LLMProviderPort(Protocol):
    def generate_incident_summary(
        self, incident: Incident, diagnostics: CiscoDiagnosticReport, rca: RCAResult
    ) -> str:
        """Generate a strictly grounded, zero-hallucination 3-paragraph summary."""
        ...

    def draft_kb_sop_article(
        self, incident: Incident, diagnostics: CiscoDiagnosticReport, rca: RCAResult
    ) -> KBSOPArticle:
        """Draft a formal Standard Operating Procedure adhering to template."""
        ...
```

---

## 2. Platform REST API Contracts (FastAPI / Service Layer)

All endpoints return standard JSON responses and enforce OpenAPI 3.1 specs.

### 2.1 Ingestion Endpoints

#### `POST /api/v1/ingest/alert`
Ingests an alert payload from SolarWinds or synthetic injector.
- **Request Body:** `SolarWindsAlertEvent`
- **Response 202 Accepted:**
```json
{
  "status": "ACCEPTED",
  "event_id": "sw-evt-99014",
  "incident_id": "inc-20260927-0042",
  "state": "ALERT_RECEIVED",
  "message": "Alert recorded, awaiting recovery or SLA window."
}
```

#### `POST /api/v1/ingest/recovery`
Ingests a recovery notification from SolarWinds.
- **Request Body:** `SolarWindsRecoveryEvent`
- **Response 200 OK:**
```json
{
  "status": "CORRELATED",
  "incident_id": "inc-20260927-0042",
  "state": "RECOVERY_RECEIVED",
  "outage_duration_seconds": 560.0
}
```

#### `POST /api/v1/ingest/diagnostic-cli`
Ingests post-recovery executed Cisco CLI diagnostic script output.
- **Request Body:** `CiscoDiagnosticPayload`
- **Response 200 OK:**
```json
{
  "status": "PROCESSED",
  "incident_id": "inc-20260927-0042",
  "state": "RCA_COMPLETE",
  "matched_rule": "R1-OPTICAL-DEGRADATION",
  "confidence": 0.96
}
```

---

### 2.2 Incident Management Endpoints

#### `GET /api/v1/incidents`
Lists correlated operational incidents with optional filtering.
- **Query Parameters:**
  - `status`: `OPEN`, `RESOLVED`, `ALL` (default: `OPEN`)
  - `severity`: `CRITICAL`, `MAJOR`, `WARNING`
  - `limit`: `int` (default: 50)
- **Response 200 OK:**
```json
{
  "total_count": 1,
  "incidents": [
    {
      "incident_id": "inc-20260927-0042",
      "device_hostname": "nyc-acc-sw01.corp.internal",
      "device_ip": "10.240.12.15",
      "state": "RCA_COMPLETE",
      "severity": "CRITICAL",
      "alert_timestamp": "2026-09-27T11:42:10Z",
      "recovery_timestamp": "2026-09-27T11:51:30Z",
      "outage_duration_seconds": 560.0,
      "probable_cause": "Optical Transceiver Degradation or Fiber Cable Micro-Bend",
      "confidence_score": 0.96,
      "is_synthetic": true
    }
  ]
}
```

#### `GET /api/v1/incidents/{incident_id}`
Returns complete incident details including parsed diagnostic telemetry, rule citations, and generated SOP.
- **Response 200 OK:** Returns composite JSON containing `Incident`, `CiscoDiagnosticReport`, `RCAEvaluation`, and `KBSOPArticle`.

#### `POST /api/v1/incidents/{incident_id}/resolve`
Marks incident as resolved and links approved SOP article.
- **Request Body:**
```json
{
  "resolution_notes": "SFP transceiver replaced on port TenGigabitEthernet1/0/1. Optical power restored to -2.3 dBm.",
  "approved_sop_id": "KB-OPT-0012",
  "resolved_by": "engineer@corp.internal"
}
```
- **Response 200 OK:**
```json
{
  "incident_id": "inc-20260927-0042",
  "state": "RESOLVED",
  "resolution_duration_sec": 950.0,
  "first_time_resolved": true
}
```

---

### 2.3 Diagnostic Parsing Test Endpoint

#### `POST /api/v1/tools/parse-cli`
Developer & test endpoint to parse arbitrary raw Cisco CLI text dumps into structured JSON.
- **Request Body:**
```json
{
  "device_model": "Cisco Catalyst 9300",
  "raw_cli_text": "nyc-acc-sw01#show interfaces TenGigabitEthernet1/0/1\nTenGigabitEthernet1/0/1 is up, line protocol is up\n  Hardware is Ten Gigabit Ethernet, address is 00a2.8912.4411\n  MTU 1500 bytes, BW 10000000 Kbit/sec\n  1845 input errors, 1845 CRC, 0 frame, 0 overrun..."
}
```
- **Response 200 OK:** Returns structured `CiscoDiagnosticReport`.

---

### 2.4 Predictive Maintenance & Health Endpoints

#### `GET /api/v1/predictive/top-at-risk`
Retrieves the **Top 10 High-Risk Devices** evaluated by the Random Forest model and telemetry feature engine.
- **Query Parameters:** `limit` (default: 10)
- **Response 200 OK:**
```json
{
  "evaluated_at": "2026-09-27T12:00:00Z",
  "total_devices_evaluated": 120,
  "top_risk_devices": [
    {
      "rank": 1,
      "device_id": "dev-c9300-nyc-01",
      "hostname": "nyc-acc-sw01.corp.internal",
      "model": "Cisco Catalyst 9300-48UXM",
      "site_code": "NYC-HQ",
      "composite_risk_score": 83.25,
      "risk_category": "CRITICAL",
      "failure_probability_14d": 0.88,
      "leading_risk_factors": [
        "Optical Rx power degraded by 5.2 dBm over trailing 14 days",
        "Rapid CRC error accumulation on TenGigabitEthernet1/0/1",
        "Unpatched Critical CVE-2023-20198 present in IOS-XE 17.09.04a"
      ],
      "recommended_preventive_action": "Schedule SFP replacement on TenGigabitEthernet1/0/1 and update firmware"
    }
  ]
}
```

#### `POST /api/v1/predictive/preventive-ticket`
Creates a proactive work order for a degrading device.
- **Request Body:**
```json
{
  "device_id": "dev-c9300-nyc-01",
  "preventive_action_type": "TRANSCEIVER_REPLACEMENT",
  "target_completion_date": "2026-10-02T18:00:00Z",
  "notes": "Replace degrading SFP before catastrophic fiber failure"
}
```
- **Response 201 Created:** Returns `PreventiveTicketEvent`.

---

### 2.5 Operational & Executive KPI Endpoints

#### `GET /api/v1/analytics/kpi-summary`
Returns operational efficiency metrics for the current reporting cycle.
- **Response 200 OK:**
```json
{
  "reporting_period": "TRAILING_30_DAYS",
  "metrics": {
    "mean_time_to_acknowledge_seconds": 12.4,
    "mean_time_to_diagnose_seconds": 38.6,
    "mean_time_to_recover_minutes": 14.8,
    "first_time_resolution_rate_pct": 89.4,
    "rca_automation_rate_pct": 91.2,
    "predictive_alerts_generated": 24,
    "preventive_tickets_created": 18,
    "incidents_prevented_count": 16,
    "kb_sop_reuse_rate_pct": 78.5,
    "estimated_downtime_hours_saved": 42.5
  }
}
```
