# Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/Architecture-Hexagonal-green.svg)](docs/04_system_architecture.md)
[![Status](https://img.shields.io/badge/Status-Engineering%20Foundation-orange.svg)](docs/10_development_roadmap.md)

An enterprise-ready, production-shaped intelligence platform that replaces manual, email-dependent network incident triage with:
1. **Automated Incident Correlation:** Unifying SolarWinds outage alerts, node recovery events, and post-recovery Cisco CLI diagnostic script outputs.
2. **Deterministic Root Cause Analysis (RCA):** Explainable rule-based diagnostic attribution with line-item evidence citations.
3. **Grounded AI Knowledge Authoring:** Zero-hallucination LLM synthesis of executive incident briefs and version-controlled Standard Operating Procedures (SOPs).
4. **Predictive Maintenance:** Machine learning (Random Forest) forecasting device failures 14 days in advance and ranking the **Top 10 High-Risk Devices**.
5. **Operational ROI Metrics:** Automated calculation of MTTA, MTTD, MTTR, First-Time Resolution Rate, and Incidents Prevented.

---

## Repository Structure

```
network-operations-intelligence/
├── app/                      # Application core and domain services
│   ├── api/                  # REST endpoints & health check
│   ├── core/                 # Configuration, structured logging, constants
│   ├── models/               # Pydantic schemas (Device, Telemetry, Incident, RCA, Risk)
│   ├── services/             # Application orchestration layer
│   ├── ingestion/            # Pluggable ingestion port (Synthetic today, M365 tomorrow)
│   ├── correlation/          # Sliding-window incident correlation engine
│   ├── rca/                  # Explainable deterministic RCA rules engine
│   ├── knowledge/            # Version-controlled Standard Operating Procedure repository
│   ├── vulnerability/        # Cisco PSIRT & CVE lifecycle enrichment
│   ├── prediction/           # Machine learning failure prediction & risk scoring
│   └── llm/                  # Grounded LLM provider abstraction (Mock / OpenAI / Azure)
├── simulator/                # High-fidelity synthetic Cisco network telemetry generator
├── data/
│   ├── synthetic/            # Simulated inventory and CLI dumps [SYNTHETIC]
│   ├── raw/                  # Ingested alerts and unprocessed logs
│   └── processed/            # Delta Lake partitions and feature stores
├── notebooks/                # PySpark & Databricks AI/BI feature exploration
├── dashboard/                # Operations & management dashboard assets
├── tests/                    # Unit, golden sample, and integration tests
├── configs/                  # YAML configurations (app.yaml, logging.yaml)
├── scripts/                  # Development and execution helper scripts
├── docs/                     # 14 approved architectural specification documents
├── .env.example              # Environment variables template (zero secrets)
├── .gitignore                # Git exclusions
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Build system, Ruff, Mypy, and Pytest configuration
└── README.md                 # This file
```

---

## Architecture Blueprint & Documentation

The complete architectural blueprint is documented in `/docs`:
- [01. Product Requirements Document (PRD)](docs/01_product_requirements_document.md)
- [02. Functional Requirements](docs/02_functional_requirements.md)
- [03. Non-Functional Requirements](docs/03_non_functional_requirements.md)
- [04. System Architecture](docs/04_system_architecture.md)
- [05. Component Architecture](docs/05_component_architecture.md)
- [06. Data Model](docs/06_data_model.md)
- [07. Event Schemas](docs/07_event_schemas.md)
- [08. API Contracts](docs/08_api_contracts.md)
- [09. Repository Structure](docs/09_repository_structure.md)
- [10. Development Roadmap](docs/10_development_roadmap.md)
- [11. Testing Strategy](docs/11_testing_strategy.md)
- [12. Security Strategy](docs/12_security_strategy.md)
- [13. Deployment Strategy](docs/13_deployment_strategy.md)
- [14. Demo Scenario](docs/14_demo_scenario.md)

---

## Quickstart & Local Setup

### 1. Prerequisites
- **Python 3.11+** installed (check with `python3.11 --version`).
- Virtual environment tool (`venv` or `conda`).

### 2. Environment Setup
```bash
# 1. Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 2. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
```

### 3. Run Quality & Health Checks
```bash
# Run test suite
pytest tests/ -v

# Run type checking
mypy app/

# Run linter
ruff check .

# Execute standalone CLI health check
python -m app.main --health
```

### 4. Start Local Development Server
```bash
# Launch FastAPI development server
./scripts/run_dev.sh
# Server starts at http://localhost:8000
# OpenAPI Swagger documentation available at http://localhost:8000/docs
```

---

## Security & Architecture Guardrails
- **No Secrets in Code:** Environment variables or cloud secret stores (Azure Key Vault, Databricks Secret Scopes) are strictly enforced.
- **Strict Grounding:** The LLM client never generates unverified technical citations; all root cause conclusions are verified against deterministic parsers.
- **Synthetic Data Transparency:** 100% of synthetic records are tagged with `"is_synthetic": true`.
- **Pluggable Ingestion:** Ingestion adapters are decoupled from business logic via `EventIngestionPort`.
