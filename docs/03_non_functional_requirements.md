# Non-Functional Requirements (NFR) Specification

## Project: Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)

---

## 1. Architectural & Engineering Principles

### NFR-1.1: Modularity & Loose Coupling (Clean Architecture / Hexagonal)
- The codebase shall strictly follow a Ports-and-Adapters (Hexagonal Architecture) structure:
  - **Domain Core:** Pure business entities, deterministic RCA rule evaluations, health scoring mathematical formulas, and data structures. Zero external framework dependencies.
  - **Application Services / Use Cases:** Orchestration of ingestion, correlation, diagnostic parsing, ML inference, and SOP generation.
  - **Adapters (Inbound):** CLI runners, REST/FastAPI endpoints, Databricks notebook triggers, synthetic event batch injectors.
  - **Adapters (Outbound):** File-based repository, SQLite/DuckDB/Delta Lake persistence, LLM provider clients, metrics sinks.
- Ingestion adapters must be pluggable: swapping synthetic event generators for Microsoft Graph API (Outlook email reader) or SolarWinds REST webhook adapters shall require zero modifications to the correlation or parsing domain logic.

### NFR-1.2: Typed Python & Strict Static Analysis
- Target runtime: **Python 3.11+**.
- 100% type annotations across all function signatures, class attributes, and module interfaces (`typing.Optional`, `typing.Union`, `typing.Protocol`, `pydantic.BaseModel`).
- Strict linting and formatting compliance with `ruff`, `mypy` (strict mode or `disallow_untyped_defs = true`), and `black`.

### NFR-1.3: Configuration-Driven Design
- No hard-coded business rules, thresholds, file paths, or model parameters.
- All configuration settings managed via structured YAML/JSON and environment variables using Pydantic `BaseSettings`:
  - Temporal correlation window (e.g. `CORRELATION_WINDOW_MINUTES = 60`)
  - RCA rule thresholds (e.g. `CRC_ERROR_THRESHOLD = 100`, `RX_POWER_DBM_THRESHOLD = -14.0`)
  - Risk scoring weight coefficients (e.g. `ML_WEIGHT = 0.50`, `VULN_WEIGHT = 0.25`, `ANOMALY_WEIGHT = 0.25`)
  - LLM provider settings (Model name, temperature, timeouts, retry counts)
- Support configuration overrides via `.env` files and environment variables without code modification.

---

## 2. Reliability, Determinism & Reproducibility

### NFR-2.1: Deterministic RCA Baseline
- Rule-based root-cause evaluation must be 100% deterministic: identical parsed CLI input must always generate the exact same rule match, confidence score, and cited evidence.
- The LLM layer is strictly an explanatory and drafting layer; it is decoupled from the foundational deterministic RCA verdict to prevent stochastic diagnostic variance.

### NFR-2.2: Reproducible Synthetic Data Generation & ML Pipelines
- Synthetic data generation routines must accept a fixed random seed (e.g., `SEED = 42`) to guarantee identical, repeatable datasets across testing and demonstration environments.
- ML feature transformation and Random Forest model training must record deterministic random states (`random_state=42`) and export versioned model metadata (`model_version`, `feature_names`, `hyperparameters`, `metrics`).

### NFR-2.3: Error Handling & Fault Isolation
- Individual command parsing failures (e.g., malformed `show interfaces` output) must not crash the entire ingestion pipeline.
- Implement explicit graceful degradation: unparseable sections are captured as raw text attachments with a parsing warning flag, while valid sections continue through RCA evaluation.
- All external API calls (e.g., LLM endpoints) must implement exponential backoff retry policies with configurable timeouts and fallback to local template-based summaries if the provider is unreachable.

---

## 3. Observability, Logging & Auditability

### NFR-3.1: Structured Logging
- Implement centralized structured logging using `structlog` or standard library `logging` with JSON formatting.
- Every log record must include contextual metadata: `timestamp`, `log_level`, `module`, `function`, `incident_id` (when available), `device_hostname`, and `execution_duration_ms`.
- Standardized log levels:
  - `DEBUG`: Diagnostic parsing tokens, regex evaluation matches.
  - `INFO`: Incident lifecycle transitions (Alert received, Recovery correlated, RCA generated).
  - `WARNING`: Telemetry threshold crossings, LLM retries, unparsed CLI syntax.
  - `ERROR`: Pipeline exceptions, ingestion failures, model inference errors.

### NFR-3.2: Comprehensive Audit Trail
- Every incident state change must be persisted with an immutable audit log capturing:
  - Timestamp of state transition
  - Triggering event or user action
  - Complete snapshot of rule evaluations and confidence metrics
  - Exact model version used for risk prediction

---

## 4. Security & DevSecOps by Design

### NFR-4.1: Secret Management & Zero Credentials in Code
- Zero API keys, passwords, connection strings, or enterprise tokens committed in source control.
- Configuration schemas must enforce injection via environment variables or secret vaults (e.g., Databricks Secret Scopes, Azure Key Vault, `.env` file excluded by `.gitignore`).
- Pre-commit scanning tools (e.g. `gitleaks`, `detect-secrets`) integrated into the CI/CD pipeline.

### NFR-4.2: Input Validation & Sanitization
- All incoming payloads (alerts, emails, CLI dumps) must be strictly validated against Pydantic schemas before domain processing.
- Input strings must be sanitized to guard against prompt injection attacks into the LLM synthesis engine. System prompts must enforce rigid boundary separators (`<diagnostic_data>` XML-style delimiters) and instruct the model to ignore any instructions embedded within raw CLI logs.

### NFR-4.3: Principle of Least Privilege & Read-Only Network Posture
- Prototype and future production architectures are designed strictly as **Read-Only / Telemetry Ingestion**.
- No automated configuration push, switch port shutdowns, or CLI write commands are permitted without explicit human approval workflows.

---

## 5. Performance & Scalability Targets

### NFR-5.1: Pipeline Latency (Prototype SLA)
| Processing Stage | Target Latency | P95 Constraint |
|---|---|---|
| Alert & Recovery Correlation | < 100 ms | < 250 ms |
| Cisco CLI Log Parsing (1000 lines) | < 300 ms | < 600 ms |
| Deterministic RCA Rule Evaluation | < 50 ms | < 100 ms |
| LLM Evidence Summary & SOP Generation | < 4.0 sec | < 7.0 sec |
| Batch Risk Scoring (100 devices) | < 1.5 sec | < 3.0 sec |
| End-to-End Incident Processing | < 5.0 sec | < 8.0 sec |

### NFR-5.2: Memory & Resource Footprint
- Prototype must run efficiently in developer environments (macOS/Linux laptop, 8GB+ RAM, Python 3.11) and Databricks single-node clusters without requiring heavyweight distributed infrastructure.

---

## 6. Testability & Quality Assurance

### NFR-6.1: Test Coverage & Test Pyramid
- Minimum target code coverage: **85%** across core domain, parsing, and correlation modules.
- Pyramid structure:
  - **Unit Tests (70%):** Fast, isolated tests for CLI parsers, individual RCA rules, mathematical risk scoring, and Pydantic schema validation.
  - **Integration Tests (20%):** End-to-end incident ingestion to RCA report generation using mock LLM and synthetic event generators.
  - **Regression & Golden File Tests (10%):** Verification of parser outputs against curated real-world Cisco CLI output sample files.
