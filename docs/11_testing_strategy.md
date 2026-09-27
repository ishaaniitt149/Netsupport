# Testing Strategy & Quality Assurance Plan

## Project: Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)

---

## 1. Quality Assurance Philosophy: The Verification Pyramid

The testing strategy is engineered to ensure 100% deterministic reliability for network diagnostics, rigorous validation of parsing accuracy against authentic Cisco CLI outputs, and mathematical correctness for predictive models.

```
                  / \
                 /   \
                / E2E \       10% End-to-End Pipeline & Demo Tests
               /-------\
              / Integr. \     20% Integration & Correlation Tests
             /-----------\
            / Unit Tests  \   70% Unit, Parser & Golden File Tests
           /---------------\
```

---

## 2. Test Dimensions & Methodologies

### 2.1 Unit Testing (`tests/unit/`)
* **Objective:** Verify isolated functional behavior of parsers, rule evaluation functions, mathematical calculations, and schema validations.
* **Scope:**
  - **Cisco Parsers (`test_cisco_parsers.py`):**
    - Feed known text blocks of `show interfaces`, `show interfaces transceiver detail`, `show env`, `show processes`, and syslog lines.
    - Assert that parsed metrics (e.g. CRC error counts, dBm values, PSU states) match expected values to within 0.01 tolerance.
    - Test edge cases: missing fields, command syntax variations between IOS-XE and NX-OS, truncated output, admin down interfaces.
  - **Deterministic RCA Rules (`test_rca_rules.py`):**
    - Construct synthetic `CiscoDiagnosticReport` fixtures representing each failure mode (Optical Degradation, PSU Fault, Memory Leak, CPU Spike, MTU Mismatch, Duplex Mismatch).
    - Assert that the rule engine selects the exact correct `rule_id` and confidence score $>0.85$.
    - Verify that `evidence_citations` accurately cite the exact offending metric and threshold.
  - **Predictive Risk Scorer (`test_risk_scoring.py`):**
    - Test scoring formula boundary values: $0.0 \le \text{Risk Score} \le 100.0$.
    - Verify sorting logic for the Top 10 High-Risk Devices.
  - **Operational Metrics (`test_metrics.py`):**
    - Provide fixed timestamp sequences and verify that MTTA, MTTD, MTTR, and FTRR match exact calculated mathematical values.

---

### 2.2 Golden Sample Testing (`tests/golden_samples/`)
* **Objective:** Prevent parser regressions against authentic Cisco command formats.
* **Methodology:**
  - Store raw, authentic CLI command output text files in `tests/golden_samples/`.
  - Pair each text file with an immutable JSON expectation file (`expected_output.json`).
  - Automated tests execute the parser across all golden files and assert deep equality against the JSON specification.

---

### 2.3 Integration Testing (`tests/integration/`)
* **Objective:** Validate component interoperability across hexagonal boundaries.
* **Scope:**
  - **Sliding-Window Correlation (`test_correlation.py`):**
    - Test normal sequence: Alert $\to$ Recovery $\to$ Diagnostic.
    - Test delayed events: Recovery arriving 45 minutes after alert (within 60-minute window).
    - Test expired events: Recovery arriving 90 minutes after alert (window expired; verify clean state transition to `UNRECOVERED_ALERT`).
    - Test interleaved events: Multiple concurrent alerts from different devices processed simultaneously without cross-talk.
  - **Ingestion Adapter Contract (`test_ingestion_adapter.py`):**
    - Verify that both the `SyntheticEventAdapter` and stubbed `M365GraphAdapter` adhere strictly to `EventIngestionPort`.

---

### 2.4 LLM Verification & Zero-Hallucination Testing
* **Objective:** Ensure the LLM summarizes technical facts without introducing fictional data.
* **Methodology:**
  - **Context Containment Test:**
    - Capture the LLM prompt context and the resulting output text.
    - Extract all IP addresses, interface identifiers (e.g., `TenGigabitEthernet1/0/1`), error numbers, and CLI command names from the generated output.
    - Assert that **every single extracted token is a subset of the prompt context**.
    - If the LLM mentions an IP address or interface not present in the input diagnostic report, the test fails immediately.
  - **Offline Determinism:** CI pipelines run against `MockLLMProvider` to ensure zero external network calls, zero token consumption costs, and 100% predictable execution.

---

### 2.5 Machine Learning Model Validation
* **Objective:** Validate the predictive maintenance Random Forest classifier.
* **Metrics:**
  - Precision, Recall, and ROC-AUC evaluated on a holdout test dataset (20% split).
  - Target constraint: Recall on imminent failure class $>75\%$.
  - Feature Importance Inspection: Verify that physically meaningful features (e.g. `optical_power_drift_rate`, `crc_error_growth_rate`, `psu_fault_flag`) rank as top contributors.

---

## 3. Test Automation & CI Pipeline Execution

### Local Development Execution
```bash
# Run complete test suite with coverage report
pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=85

# Run only fast unit tests
pytest tests/unit/ -v

# Run golden sample parser tests
pytest tests/golden_samples/ -v
```

### GitHub Actions CI Workflow (`.github/workflows/ci.yml`)
1. **Linting & Code Style:** `ruff check src/ tests/` and `black --check src/ tests/`.
2. **Static Type Checking:** `mypy --config-file pyproject.toml src/`.
3. **Security Analysis:** `bandit -r src/` and `gitleaks detect`.
4. **Automated Testing:** `pytest tests/ --cov=src --cov-fail-under=85`.
