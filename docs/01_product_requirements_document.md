# Product Requirements Document (PRD)

## Project Title
**Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)**

**Status:** Draft / Architecture Baseline  
**Version:** 1.0.0  
**Target Delivery:** Working Prototype (Production-Shaped)  
**Authors:** Principal Software Architect, Senior Python Engineer, Senior Data Engineer, ML Engineer, Network Automation Engineer, DevSecOps Engineer  

---

## 1. Executive Summary
Modern enterprise network operations face high operational toil, delayed Root Cause Analysis (RCA), and repetitive manual firefighting. In our current enterprise workflow:
1. SolarWinds monitors Cisco routers, switches, firewalls, and wireless controllers.
2. Device outages or degradation (packet loss, link flapping) trigger email alerts via Microsoft Outlook.
3. Once connectivity recovers, SolarWinds executes an automated CLI command script capturing diagnostic state (`show tech-support`, `show log`, `show interfaces`, etc.).
4. A second email containing the diagnostic output is delivered to network operations engineers.
5. Network engineers manually correlate the two emails, read raw CLI dumps, diagnose the root cause, manually execute remediations, resolve service desk tickets, and write ad-hoc KB/SOP articles.

The **Network Operations Intelligence & Predictive Maintenance Platform** transforms this reactive, email-dependent, manual process into an automated, explainable, and predictive operational intelligence engine. The platform ingests telemetry and alert streams, correlates alerts with recovery and diagnostic diagnostics into a single unified incident, parses Cisco CLI outputs deterministically, generates explainable root causes, leverages a strictly grounded LLM for SOP/KB draft generation, and trains machine learning models to forecast device failures before they impact enterprise SLA.

---

## 2. Problem Statement & Business Opportunity
* **Alert Fragmentation:** Outage alerts, recovery notifications, and diagnostic logs arrive in disconnected emails, causing context switching and delayed correlation.
* **Manual RCA Fatigue:** Engineers spend 30–90 minutes per incident sifting through thousands of lines of raw Cisco logs (`show log`, `show interface counters`, `show processes cpu`, optical transceiver telemetry) to find known patterns like CRC mismatches, memory leaks, PSU degradation, or BGP flaps.
* **Knowledge Loss & Repetitive Toil:** Resolved incidents rarely feed into structured, version-controlled Knowledge Bases (KB) or Standard Operating Procedures (SOP), resulting in repeated diagnosis of identical issues.
* **Zero Proactivity:** Operations remains purely reactive; devices fail catastrophically when subtle degradation patterns (rising CRC rates, thermal drift, buffer exhaustion, flash corruption) were detectable days or weeks prior.

---

## 3. Product Vision & Goals
Deliver a **production-shaped, modular prototype** that operates on high-fidelity synthetic Cisco/SolarWinds telemetry today, and transitions seamlessly to direct SolarWinds API, Microsoft Graph API (Outlook), and Databricks lakehouse integration tomorrow without altering the core domain logic.

### Key Objectives:
1. **Unify Ingestion & Correlation:** Aggregate SolarWinds down/degradation alerts, node recoveries, and Cisco CLI RCA outputs into a cohesive stateful incident entity.
2. **Deterministic & Explainable RCA:** Use rule-based pattern matching and telemetry parsing for 100% auditable diagnostic attribution, augmented (not replaced) by an LLM for natural-language executive summaries and KB/SOP drafts.
3. **Predictive Maintenance & Health Scoring:** Train a supervised Random Forest model on historical telemetry and degradation trends to score device failure risk (0–100) and publish a daily "Top 10 At-Risk Devices" dashboard with recommended preventive actions.
4. **Quantifiable Operational ROI:** Continuously calculate executive and operational metrics:
   - Mean Time to Acknowledge (MTTA)
   - Mean Time to Diagnose (MTTD)
   - Mean Time to Recover (MTTR)
   - First-Time Resolution Rate (FTRR)
   - Predictive Alerts Generated vs. Incidents Prevented
   - KB Article Reuse Rate
   - RCA Automation Rate

---

## 4. User Personas & Target Audiences

| Persona | Role | Primary Goals | Pain Points with Current System |
|---|---|---|---|
| **P1: Tier 1/2 NOC Engineer** | Incident Triage & Resolution | Fast triage, instant parsed diagnostic summaries, clear actionable remediation checklists. | Drowning in raw CLI email dumps, manually opening multiple tickets, searching fragmented wikis. |
| **P2: Network Automation / Tier 3 Architect** | Root Cause Attribution & Stability | Auditable RCA rules, automated SOP creation, firmware lifecycle management, vulnerability mitigation. | Inconsistent documentation, lack of telemetry correlation, zero historical baseline visibility. |
| **P3: IT Operations & Network Director** | SLA, Budgeting & Risk Management | MTTR/MTTA reduction, proactive hardware replacement scheduling, ROI tracking on automation. | Unplanned outages causing business downtime, reactive budgeting, lack of executive KPI dashboards. |

---

## 5. High-Level Capabilities & Scope

### In Scope (Prototype Phase):
- **Synthetic Data Engine:** Realistic simulation of Cisco inventory (Catalyst 9300/9500, Nexus 9000, ISR 4400/Catalyst 8300, ASR 1000), SolarWinds alert emails, node recovery notifications, and Cisco CLI RCA dumps marked explicitly as `[SYNTHETIC]`.
- **Event Correlation Engine:** Window-based correlation matching node outage alerts, recovery timestamps, and diagnostic outputs by device FQDN/IP.
- **Cisco Diagnostic Parsing Engine:** Multi-command structured parser extracting structured metrics (CRC counters, optics dBm, CPU spikes, memory leaks, PSU state, MTU mismatch, route flaps).
- **Explainable Rule-Based RCA Engine:** Transparent decision-tree/rule matching producing confidence-scored probable causes.
- **Provider-Agnostic LLM Integration:** Abstracted client (OpenAI/Azure OpenAI/Anthropic/Local Mock) for KB drafting and plain-English RCA synthesis, enforcing strict zero-hallucination prompts referencing only parsed evidence.
- **Predictive Risk Engine:** PySpark/scikit-learn Random Forest classifier producing composite Risk Scores (0.0 to 1.0) and ranking Top 10 high-risk devices.
- **Reporting & Operational Metrics:** In-memory / file-backed telemetry calculations for MTTA, MTTD, MTTR, FTRR, KB Reuse, and Automation Rate.
- **Operations & Management Dashboards:** Prototype dashboard specification for Databricks AI/BI (and responsive local UI prototype).

### Out of Scope (Prototype Phase - Non-Goals):
- Live production connection to corporate SolarWinds, Microsoft 365 Outlook mailboxes, or Teams webhooks.
- Multi-node Kubernetes / EKS / ECS clusters, Kafka streaming clusters, or external managed RDS databases.
- Automated closed-loop network configuration push (read-only diagnostic and recommendations only).

---

## 6. Success Metrics & Key Performance Indicators (KPIs)

| KPI | Baseline (Manual Workflow) | Target (NOIPMP Prototype) | Measurement Formula |
|---|---|---|---|
| **Mean Time to Diagnose (MTTD)** | 45 minutes | < 2 minutes | `Sum(Diagnose_Time - Alert_Time) / Total_Incidents` |
| **RCA Automation Rate** | 0% | > 85% | `(Automated_RCA_Incidents / Total_Incidents) * 100` |
| **First-Time Resolution Rate** | 62% | > 85% | `(Incidents_Resolved_No_Reopen / Total_Incidents) * 100` |
| **Predictive Risk Accuracy (Recall)** | 0% (Reactive) | > 75% | `True_Predicted_Failures / Actual_Degradations` |
| **SOP/KB Generation Time** | 2–5 days (Manual) | < 30 seconds (Draft) | Automated pipeline draft generation latency |
| **Incidents Prevented** | 0 | Quantified per cycle | Preventive work orders executed prior to node down |

---

## 7. Assumptions, Dependencies & Constraints
1. **Synthetic Fidelity:** Synthetic logs must mirror genuine Cisco IOS-XE / NX-OS command output syntax (`show interfaces`, `show logging`, `show environment power`, `show processes cpu sorted`).
2. **Strict Grounding:** The LLM module must never invent technical evidence, CLI commands, or IP addresses not present in the input diagnostic payload.
3. **Pluggable Ingestion:** The code must decouple the ingestion boundary (synthetic files or queues) from the incident correlation and analysis engine.
