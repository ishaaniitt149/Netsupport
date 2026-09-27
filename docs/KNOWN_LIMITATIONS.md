# Known Limitations

The NOIPMP prototype is built to production standards, but currently has the following defined architectural and operational limitations:

## 1. Deterministic RCA Dependency
- **Limitation:** The RCA engine relies entirely on the format of Cisco CLI outputs (e.g., `show interfaces`, `show tech-support`).
- **Impact:** Firmware updates from the vendor that alter CLI output spacing, capitalization, or terminology will break the regex and parsing engines. 
- **Mitigation:** The parser must be maintained via unit tests aligned with new firmware releases.

## 2. LLM Capabilities and Trust
- **Limitation:** LLMs are restricted strictly to summarization via Grounding Contracts. They cannot "discover" network issues not already flagged by the deterministic engine.
- **Impact:** The LLM will confidently state "Not available" if the deterministic engine fails to parse a metric, even if a human could deduce the issue from raw logs.
- **Mitigation:** Fallback mechanisms to raw logs are allowed via strict configuration (`LLM_ALLOW_RAW_INFRASTRUCTURE_DATA`), but this requires private model hosting.

## 3. Predictive Model Window (Temporal Leakage)
- **Limitation:** The current Random Forest ML model requires a 30-day historical lookback window to predict a 14-day horizon. 
- **Impact:** Devices newly provisioned to the network cannot receive accurate predictive risk scores until sufficient baseline telemetry is established.

## 4. Incident Prevention Attribution
- **Limitation:** It is logically difficult to prove a negative (that an outage *would* have happened if not prevented).
- **Impact:** The "Incidents Prevented" KPI is highly conservative and strict. It may under-report actual prevented outages to maintain absolute data integrity.

## 5. Vulnerability Matching
- **Limitation:** CVE matching is string-based and tabular.
- **Impact:** It does not account for complex network topologies (e.g., a vulnerable device that is securely isolated behind a firewall might be flagged with the same criticality as an edge-facing router).
