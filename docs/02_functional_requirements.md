# Functional Requirements Specification (FRS)

## Project: Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)

---

## 1. Module FR-1: Synthetic Data Generation Engine

### FR-1.1: Device Inventory Simulation
- The engine shall simulate an enterprise network inventory of at least 100 heterogeneous Cisco devices covering:
  - **Core/Aggregation Switches:** Cisco Catalyst 9500, Cisco Nexus 9300
  - **Access Layer Switches:** Cisco Catalyst 9300 (StackWise-480 stacks)
  - **WAN Edge / SD-WAN Routers:** Cisco ISR 4451, Cisco Catalyst 8300, Cisco ASR 1001-X
  - **Firewalls / Security:** Cisco Firepower 2100/4100
- Each device entity must include: `device_id`, `hostname`, `ip_address`, `device_model`, `os_version` (IOS-XE / NX-OS), `serial_number`, `site_code`, `rack_location`, `role` (Core, Dist, Access, WAN), `hardware_eol_date`, and `installed_transceivers`.
- All generated records must contain a metadata tag: `"is_synthetic": true`.

### FR-1.2: Telemetry Simulation
- The engine shall generate periodic time-series telemetry (e.g. 5-minute sampling interval) for each device:
  - CPU utilization (5s, 1m, 5m averages)
  - Memory utilization (used bytes, free bytes, fragmentation index)
  - Temperature sensors (Inlet, ASIC, Outlet) in Celsius
  - Power supply unit status (PSU1, PSU2: Normal, Warning, Fault)
  - Interface-level metrics: In/Out Octets, In/Out Errors, CRC error rate, Input packet discards, Transceiver optical Tx/Rx power (dBm), Link Flap count.
- The engine shall support injecting targeted anomaly profiles (e.g. Memory Leak, Optical Transceiver Degradation, CRC Accumulation, Thermal Runaway, PSU Redundancy Loss).

### FR-1.3: Alert & Recovery Email Simulation (SolarWinds Pattern)
- **Down/Degradation Alert Generation:** Formats SolarWinds alert payloads matching standard email formats (`Subject: ALERT: Node <Hostname> is Down/Experiencing Packet Loss`).
  - Contains: Alert timestamp, Alert ID, Node IP, Node Name, Severity (Critical, Warning), Trigger Condition.
- **Recovery Notification Generation:** Formats SolarWinds recovery payloads (`Subject: RECOVERY: Node <Hostname> is Up`).
  - Contains: Recovery timestamp, Alert ID reference, Node IP, Node Name, Duration of Outage.

### FR-1.4: Cisco Diagnostic Command Output Generation (RCA Script Simulation)
- The engine shall generate realistic Cisco CLI output corresponding to automated script triggers upon node recovery.
- Must include syntactically authentic output blocks for:
  - `show version`
  - `show logging | include ERROR|CRIT|WARN`
  - `show interfaces [interface_id]` (including input errors, CRC, collisions, framing errors)
  - `show interfaces transceiver detail` (Tx/Rx optical power in dBm, threshold alarms)
  - `show environment power` & `show environment temperature`
  - `show processes cpu sorted | exclude 0.00`
  - `show processes memory sorted`
  - `show ip route summary` / `show ip bgp summary`

---

## 2. Module FR-2: Ingestion & Event Correlation Engine

### FR-2.1: Multi-Stream Event Ingestion
- Ingest three decoupled streams:
  1. SolarWinds Outage / Degradation Alerts
  2. SolarWinds Node Recovery Events
  3. Cisco Diagnostic Command Output Payloads
- Abstract the ingestion layer with an `EventIngestionPort` interface to allow immediate swap between Local Synthetic Event Reader, File/Directory Watcher, and future Microsoft Graph API / Webhook connectors.

### FR-2.2: Stateful Incident Correlation
- The correlation engine shall maintain an active temporal sliding window (configurable, default: 60 minutes).
- Correlate events based on composite key: `(device_hostname, device_ip, alert_id / time_window)`.
- Life cycle states of an Incident:
  - `ALERT_RECEIVED` -> `RECOVERY_RECEIVED` -> `DIAGNOSTIC_ATTACHED` -> `ANALYZING` -> `RESOLVED` / `ESCALATED`.
- If an alert receives no recovery within the SLA threshold, mark incident as `OUTAGE_ONGOING`.
- If diagnostic output arrives without an open alert, synthesize an `ORPHAN_DIAGNOSTIC` incident for unmonitored anomalies.

---

## 3. Module FR-3: Cisco Diagnostic Parsing Engine

### FR-3.1: Command-Specific Deterministic Parsers
- **Parser 1: `show interfaces`:** Extracts Interface Name, Status (up/down/admin down), Line Protocol, Duplex/Speed, MTU, In/Out packets, Input errors, CRC errors, Frame errors, Overrun, Output errors, Collisions.
- **Parser 2: `show interfaces transceiver detail`:** Extracts Optical Transceiver type (SFP-10G-SR, QSFP-40G, etc.), Tx Power (dBm), Rx Power (dBm), Current (mA), Voltage (V), and Alarm/Warning flags (High/Low Tx/Rx power).
- **Parser 3: `show environment` (Power & Temp):** Extracts PSU IDs, PSU Status (OK, Faulty, Off), Temperature sensor names, Current value (°C), Threshold limit (°C), Status (Normal, Warning, Critical).
- **Parser 4: `show processes cpu & memory`:** Extracts Total CPU %, Top 5 consuming processes (e.g. `BGP Router`, `IP Input`, `Spanning Tree`), Total Free Memory, Total Used Memory.
- **Parser 5: `show logging`:** Normalizes syslog lines into: Timestamp, Facility, Severity (0–7), Mnemonic (e.g., `LINK-3-UPDOWN`, `BGP-5-ADJCHANGE`, `PLATFORM-3-ELEMENT_WARNING`), and Message Body.

### FR-3.2: Structured Telemetry Output
- Output must be an immutable typed data structure (`CiscoDiagnosticReport`) containing standardized sub-models for interfaces, environment, logs, and system load.

---

## 4. Module FR-4: Explainable Rule-Based RCA Engine

### FR-4.1: Deterministic RCA Rules Catalog
The engine shall evaluate parsed diagnostics against an auditable rule catalog:
- **Rule R1: Physical Layer Degradation / Bad Fiber/Cable:**
  - *Condition:* `crc_errors > 100` within 15 min AND `rx_power_dbm < rx_low_alarm_threshold` OR `input_errors` rapidly increasing.
  - *Root Cause:* "SFP Transceiver or Physical Fiber Patch Cable Degradation."
  - *Confidence:* 95%.
- **Rule R2: Duplex / Speed Mismatch:**
  - *Condition:* `late_collisions > 50` AND `duplex == "Half"` while remote peer is "Full".
  - *Root Cause:* "Duplex mismatch between connected switchport and endpoint."
  - *Confidence:* 90%.
- **Rule R3: Hardware Power Supply Failure:**
  - *Condition:* `psu_status == "Faulty"` OR syslog contains `PLATFORM-3-ELEMENT_WARNING: Power supply module failed`.
  - *Root Cause:* "Internal Power Supply Unit (PSU) Hardware Failure."
  - *Confidence:* 98%.
- **Rule R4: Memory Leak / Resource Depletion:**
  - *Condition:* `free_memory_bytes < 5% of total` AND top process memory monotonically increasing over 3 telemetry windows.
  - *Root Cause:* "IOS-XE Software Memory Leak in Process `<process_name>`."
  - *Confidence:* 88%.
- **Rule R5: Control Plane CPU Starvation / STP Loop / BGP Churn:**
  - *Condition:* `cpu_5min > 90%` AND top process in (`BGP Router`, `IP Input`, `Spanning Tree`) AND syslog contains routing flaps.
  - *Root Cause:* "Control Plane Exhaustion caused by Routing/Topology Flapping."
  - *Confidence:* 92%.
- **Rule R6: MTU Size Mismatch:**
  - *Condition:* Syslog shows `OSPF-4-ERRRCV: ... Received packet does not match neighbor MTU` or giant packet discards increasing.
  - *Root Cause:* "Interface MTU Mismatch with Upstream Peer."
  - *Confidence:* 96%.

### FR-4.2: Evidence Attachment
- Every rule evaluation must generate an `RCAEvaluationResult` stating:
  - `matched_rule_id`
  - `probable_cause`
  - `confidence_score` (0.0 to 1.0)
  - `supporting_evidence_citations` (exact parsed values: e.g. `CRC=1452`, `Rx_dBm=-19.4 dBm [Alarm < -14.0]`, `Log_Mnemonic=PLATFORM-3-ELEMENT_WARNING`).
  - `recommended_remediation_actions` (ordered list of concrete steps).

---

## 5. Module FR-5: LLM-Assisted Evidence Synthesis & KB/SOP Drafting

### FR-5.1: Grounded Prompting & Zero-Hallucination Guardrails
- The LLM service shall receive:
  1. The normalized incident metadata (device, timestamps, outage duration).
  2. The deterministic rule-based RCA findings and exact supporting evidence citations.
  3. Pre-indexed relevant historical resolutions / KB entries.
- System prompt constraints:
  - "You are an expert Cisco Network Operations Assistant. You MUST strictly rely ONLY on the provided telemetry, rule evaluation citations, and syslog snippets. NEVER invent IP addresses, interface numbers, error counts, or diagnostic commands not present in the prompt."

### FR-5.2: LLM Output Generation
- The LLM shall produce two artifacts:
  1. **Executive Incident Summary:** A concise 3-paragraph plain-language explanation of what occurred, why it failed, how it recovered, and what must be inspected.
  2. **Draft SOP/KB Article:** Formatted in standard Markdown adhering to the corporate template:
     - Document ID / Revision
     - Symptoms & Problem Description
     - Root Cause Summary
     - Diagnostic Evidence Table
     - Step-by-Step Remediation Procedure
     - Rollback Plan
     - Verification Commands

### FR-5.3: LLM Provider Abstraction
- Implements an interface `LLMProviderPort` supporting:
  - `MockLLMProvider` (local deterministic template generator for offline execution and CI tests).
  - `OpenAICompatibleProvider` (Azure OpenAI, OpenAI, or local Ollama).
  - Configuration-driven selection without code edits.

---

## 6. Module FR-6: Incident & KB/SOP Lifecycle Management

### FR-6.1: Incident Store
- Persist correlated incidents, parsed reports, and RCA findings with full audit timestamps.
- Support querying by: `device_id`, `site_code`, `root_cause_category`, `severity`, `time_range`.

### FR-6.2: Version-Controlled Knowledge Base (KB)
- Store all generated and reviewed KB/SOP articles in a versioned repository structure (`docs/kb/<category>/<doc_id>_v<version>.md` and metadata index).
- Support tracking of article status: `DRAFT` -> `UNDER_REVIEW` -> `APPROVED` -> `DEPRECATED`.
- Support tracking reuse metrics: count how many times an approved KB article was matched and applied to subsequent incidents.

---

## 7. Module FR-7: Vulnerability & Firmware Lifecycle Enrichment

### FR-7.1: Device Inventory Enrichment
- Cross-reference device OS versions against a simulated Cisco PSIRT / CVE security advisory database.
- Tag devices with:
  - Known CVEs and CVSS Severity scores.
  - End-of-Life (EOL) / End-of-Support (EOS) milestones.
  - Recommended target "Golden Image" firmware version.

---

## 8. Module FR-8: Predictive Maintenance & Risk Scoring Engine

### FR-8.1: Feature Engineering
- Generate aggregated device health features over a sliding observation window (7-day / 30-day lookback):
  - `rolling_7d_crc_error_growth_rate`
  - `rolling_7d_link_flap_count`
  - `rolling_7d_avg_cpu_util` and `cpu_spike_frequency`
  - `optical_power_drift_dbm_per_week`
  - `power_supply_redundancy_degraded_flag`
  - `device_age_years` and `hardware_eol_flag`
  - `firmware_vulnerability_count` (high/critical CVEs)
  - `historical_incident_count_30d`

### FR-8.2: Supervised ML Failure Prediction Model
- Train a **Random Forest Classifier** (`scikit-learn` / PySpark MLlib compatible).
- **Target Variable:** Binary flag `device_will_experience_incident_next_14d` (0 = Healthy, 1 = Failure/Outage Expected).
- Model outputs:
  - Class prediction and probability `P(Failure)`.
  - Feature importances (explainability).

### FR-8.3: Composite Health & Risk Scoring
- Compute `Device_Risk_Score` on a scale of 0 to 100:
  - `Risk_Score = (ML_Probability * 50) + (Hardware_Vulnerability_Penalty * 25) + (Telemetry_Anomaly_Penalty * 25)`.
- Categorize risk levels:
  - `LOW` (0–39), `MEDIUM` (40–69), `HIGH` (70–84), `CRITICAL` (85–100).
- Generate the **Top 10 High-Risk Devices** ranking with associated primary risk drivers.

### FR-8.4: Proactive Preventive Action Generation
- For each device in High or Critical tier, auto-generate recommended preventive work orders:
  - Example: "Replace SFP Transceiver on TenGigabitEthernet1/0/1 (Rx drift: -3.8 dBm over 14 days)."
  - Example: "Schedule Planned Reboot / IOS-XE Golden Image Patch (Memory leak detected in process 'BGP Router')."

---

## 9. Module FR-9: Operational & Management Metrics Engine

### FR-9.1: Automated Metric Computations
The engine shall dynamically aggregate and compute:
1. **MTTA (Mean Time to Acknowledge):** Duration between alert ingestion and triage assignment.
2. **MTTD (Mean Time to Diagnose):** Duration between alert ingestion and successful automated RCA generation.
3. **MTTR (Mean Time to Recover):** Duration between outage start and device operational recovery.
4. **First-Time Resolution Rate (FTRR):** Percentage of incidents resolved without reopening within 72 hours.
5. **Predictive Alerts Generated:** Count of proactive alerts issued prior to device outage.
6. **Preventive Tickets Created:** Proactive maintenance tickets raised based on ML risk scores.
7. **Incidents Prevented:** Devices with proactive tickets completed that avoided simulated catastrophic failures.
8. **KB Reuse Rate:** Percentage of incoming incidents matched to existing approved SOPs.
9. **RCA Automation Rate:** Percentage of incidents whose root cause was identified without human manual parsing.

---

## 10. Module FR-10: Dashboards & Reporting Specification

### FR-10.1: Operations Dashboard (NOC View)
- Active Incident Queue with severity, device FQDN, correlated recovery status, and automated RCA badge.
- Real-time diagnostic drilldown: side-by-side parsed CLI tables vs. raw CLI logs.
- Interactive SOP/KB preview with one-click resolution confirmation.

### FR-10.2: Predictive Maintenance Dashboard (Engineering View)
- Top 10 High-Risk Devices leaderboard with Risk Score breakdown and recommended preventive action.
- Telemetry trend charts: CRC degradation curves, Optical power drift, Memory depletion trajectories.

### FR-10.3: Executive KPI Dashboard (Management View)
- Trend cards for MTTA, MTTD, MTTR, Automation Rate, and Incidents Prevented.
- Cost avoidance estimator based on prevented downtime hours.
