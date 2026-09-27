# Security Architecture and Threat Model

## 1. Overview
This document outlines the security controls, data classification, and threat modeling for the Network Operations Intelligence platform. As a platform dealing with potentially sensitive infrastructure telemetry and diagnostics, we apply strict data handling guidelines.

## 2. Data Classification
| Data Type | Classification | Handling Guidelines |
| :--- | :--- | :--- |
| **Raw Command Output** (e.g. `show tech-support`) | **Sensitive** | May contain IP addresses, route tables, auth tokens. Must be scrubbed or parsed locally. **Never** send to external LLMs without explicit config flag. |
| **Telemetry / KPIs** (e.g. CPU %, Packet Loss %) | **Internal** | Safe for aggregation and anomaly detection. |
| **Incident Metadata** (e.g. Alert IDs, start time) | **Internal** | Safe to use in summaries. |
| **LLM Summaries & KB Drafts** | **Internal** | Contains aggregated knowledge; requires human review before approval. |

## 3. Secret Management
* **Environment Variables**: All secrets (like `OPENAI_API_KEY`) are passed via environment variables (or `.env` locally). They are **never** hardcoded.
* **LLM Provider Abstraction**: The `LLM_API_KEY` is read only once during the initialisation of the `OpenAICompatibleProvider`. It is not logged or exposed in tracebacks.
* **File Permissions**: The `.env` file should be secured (`chmod 600`) and excluded via `.gitignore`.

## 4. Input Validation & Boundaries
* **Strict Typing**: The system relies heavily on Pydantic V2 models. Any invalid data types or malformed inputs from external integrations (like Webhooks or Kafka) are automatically rejected before processing.
* **Path Traversal Mitigation**: File-backed storage (like `KBStore`) explicitly sanitizes inputs (e.g., `kb_id`) to prevent directory traversal (`../` payloads).

## 5. Prompt Injection & LLM Data Leakage
* **Grounding Contracts**: Every prompt submitted to an LLM contains a strict, immutable preamble instructing the model to rely solely on the provided context.
* **Data Scrubbing by Default**: By default (`LLM_ALLOW_RAW_INFRASTRUCTURE_DATA=False`), raw diagnostic outputs (which may contain sensitive IP schemas) are **stripped** before sending to the LLM. Only pre-parsed, deterministic KPI counters (e.g., CRC Errors) are sent.

## 6. Threat Model summary
1. **Threat**: Attacker injects malicious payload into device hostname/telemetry to manipulate LLM summary.
   * **Mitigation**: Grounding contracts and Pydantic validation. The LLM cannot execute code, and its output is strictly reviewed.
2. **Threat**: Accidental leakage of network topology via `show run`.
   * **Mitigation**: The determinisitic RCA engine parses the output locally. The raw text is discarded before hitting the LLM API unless explicitly opted-in for private models.
3. **Threat**: Path Traversal in KB Storage.
   * **Mitigation**: Sanitization of `kb_id` rejecting `/` and `\`.

*Note: The platform provides architectural safeguards, but does not claim specific compliance (e.g., SOC2/ISO27001) out of the box. Organisations must apply their own compliance reviews before production deployment.*
