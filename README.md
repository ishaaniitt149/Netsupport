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

Welcome! Follow this beginner-friendly guide to get the platform running locally. We use `make` commands to simplify the setup process. (If you are on Windows and don't have `make`, you can run the commands directly as listed inside the `Makefile`.)

### 1. How to install Python
Ensure you have **Python 3.11** or higher installed. 
- **Mac/Linux**: We recommend using [Homebrew](https://brew.sh/): `brew install python@3.11`
- **Windows**: Download the installer from the [official Python website](https://www.python.org/downloads/). Ensure you check "Add Python to PATH" during installation.
You can verify your installation by running `python3 --version` in your terminal.

### 2. How to create environment
We use an isolated virtual environment to manage dependencies so they don't conflict with your system.
Simply run:
```bash
make setup
```
*(This command creates a `.venv` directory and installs all required packages from `requirements.txt`.)*

Activate the environment before proceeding:
- **Mac/Linux**: `source .venv/bin/activate`
- **Windows**: `.venv\Scripts\activate`

### 3. How to configure .env
The `make setup` command automatically copies the `.env.example` file to `.env` for you. 
Open the `.env` file in your editor and:
1. Provide your `LLM_API_KEY` (if you intend to use OpenAI instead of the `mock` provider).
2. Set `LLM_PROVIDER=openai` (default is `mock` for local testing without an API key).
*Note: Never commit your `.env` file to version control.*

### 4. How to generate data
The system relies on synthetic device and telemetry data for simulations. Generate the baseline data by running:
```bash
make generate-data
```

### 5. How to run the application
Start the core FastAPI backend server by running:
```bash
make run
```
The API will be available at `http://localhost:8000`. You can view the interactive documentation at `http://localhost:8000/docs`.

### 6. How to run tests
To ensure everything is working correctly, run the comprehensive test suite:
```bash
make test
```
This executes all unit and integration tests using `pytest`.

### 7. How to run demo mode
We provide an interactive Engineer UI built with Streamlit to simulate an end-to-end incident lifecycle.
To launch the demo interface:
```bash
make demo
```
This will open the UI in your web browser, where you can click "RUN DEMO SCENARIO" to watch an incident unfold from predictive warning through RCA and knowledge base creation.

### 8. How to connect Databricks
The platform uses a Medallion Architecture (Bronze/Silver/Gold) on Databricks for distributed data processing and AI/BI dashboarding.
To connect:
1. Ensure your Databricks cluster is running.
2. Provide your Databricks host and token in the `.env` file (e.g., `DATABRICKS_HOST` and `DATABRICKS_TOKEN`).
3. Deploy the notebooks located in the `/notebooks` directory to your Databricks workspace.

### 9. How to troubleshoot common failures
- **Command Not Found (`make`)**: If you are on Windows, you can install `make` via Chocolatey (`choco install make`) or simply open the `Makefile` and run the `python -m ...` commands directly.
- **Port 8000 Already in Use**: If `make run` fails because the port is taken, edit the `APP_PORT` variable in your `.env` file to a different port (e.g., 8080).
- **ModuleNotFoundError**: Ensure your virtual environment is activated (`source .venv/bin/activate`) before running any Python or Make commands.
- **Missing API Key Error**: If you see LLM errors, ensure your `.env` contains a valid `LLM_API_KEY` or switch `LLM_PROVIDER` back to `mock`.

---

## Security & Architecture Guardrails
- **No Secrets in Code:** Environment variables or cloud secret stores (Azure Key Vault, Databricks Secret Scopes) are strictly enforced.
- **Strict Grounding:** The LLM client never generates unverified technical citations; all root cause conclusions are verified against deterministic parsers.
- **Synthetic Data Transparency:** 100% of synthetic records are tagged with `"is_synthetic": true`.
- **Pluggable Ingestion:** Ingestion adapters are decoupled from business logic via `EventIngestionPort`.
