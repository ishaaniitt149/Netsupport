# Technical Architecture

NOIPMP employs a modular, hexagonal architecture designed for determinism, enterprise security, and massive scale. 

## Core Modules

1. **Ingestion & Correlation Engine**
   - Ingests alerts, recovery events, and raw telemetry via a pluggable adapter.
   - Correlates independent events into unified incident records using a temporal sliding window.

2. **Deterministic Root Cause Analysis (RCA) Engine**
   - Bypasses LLM hallucinations by using a deterministic, rule-based parsing engine (e.g. regex and threshold logic) against Cisco CLI outputs (`show tech-support`, `show interfaces`).
   - Maps raw text to structured operational evidence.

3. **Predictive Risk & Machine Learning**
   - Utilizes a `joblib`-backed Random Forest model to forecast network device failures up to 14 days in advance based on a 30-day lookback window of telemetry anomalies.
   - Outputs a concrete Probability of Failure and triggers Preventive Actions via a Finite State Machine (FSM).

4. **Grounded Knowledge Base (KB) Authoring**
   - Leverages a Large Language Model (LLM) strictly for summarization and drafting.
   - Uses a "Grounding Contract" to ensure the LLM only summarizes deterministic RCA evidence and cannot invent commands, infrastructure topologies, or CVEs.

5. **Databricks Medallion Architecture**
   - **Bronze**: Raw ingest of synthetic alerts, RCA text, and telemetry.
   - **Silver**: Structured tables (devices, incidents, parsed diagnostics).
   - **Gold**: Aggregated AI/BI dashboards (Device Health, Predictive Risk, KPI Metrics).

## Security Guardrails
- **No LLM Data Leakage**: By default, raw infrastructure data (which may contain IPs or routes) is stripped and parsed locally. The LLM only receives parsed, abstract metrics (e.g., `CRC Errors: 100`).
- **No Hallucinated CVEs**: Vulnerability (CVE) matching is strictly tabular and deterministic. 
