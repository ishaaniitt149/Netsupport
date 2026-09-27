# Repository Structure & Layout Specification

## Project: Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)

---

## 1. Top-Level Directory Tree

```
office project/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Linting, formatting, pytest & typecheck
│       └── security-scan.yml      # Gitleaks & Bandit vulnerability scan
├── config/
│   ├── default.yaml               # Baseline application configuration
│   ├── correlation_rules.yaml     # Time windows and correlation parameters
│   ├── rca_rules.yaml             # Thresholds and rule catalog for deterministic RCA
│   └── ml_model_config.yaml       # Random Forest hyperparameters and feature weights
├── data/
│   ├── synthetic/
│   │   ├── devices.json           # Seed inventory of Cisco devices [SYNTHETIC]
│   │   ├── sample_cli_dumps/      # Curated raw Cisco CLI output scenarios
│   │   │   ├── scenario_optical_degrade.txt
│   │   │   ├── scenario_psu_failure.txt
│   │   │   ├── scenario_memory_leak.txt
│   │   │   └── scenario_mtu_mismatch.txt
│   │   └── vulnerabilities.json   # Simulated Cisco PSIRT CVE mapping
│   └── delta_lake/                # Local Parquet/Delta storage for prototype
│       ├── dim_devices/
│       ├── fact_telemetry/
│       ├── fact_incidents/
│       └── fact_risk_scores/
├── docs/
│   ├── 01_product_requirements_document.md
│   ├── 02_functional_requirements.md
│   ├── 03_non_functional_requirements.md
│   ├── 04_system_architecture.md
│   ├── 05_component_architecture.md
│   ├── 06_data_model.md
│   ├── 07_event_schemas.md
│   ├── 08_api_contracts.md
│   ├── 09_repository_structure.md
│   ├── 10_development_roadmap.md
│   ├── 11_testing_strategy.md
│   ├── 12_security_strategy.md
│   ├── 13_deployment_strategy.md
│   ├── 14_demo_scenario.md
│   ├── README.md
│   └── kb/                        # Version-controlled Standard Operating Procedures
│       ├── physical_optical/
│       │   └── KB-OPT-0012_v1.md
│       ├── hardware_power/
│       │   └── KB-PWR-0004_v1.md
│       └── routing_control_plane/
│           └── KB-RTE-0008_v1.md
├── notebooks/                     # Databricks PySpark & ML Exploration Notebooks
│   ├── 01_telemetry_feature_engineering.py
│   ├── 02_random_forest_training.py
│   └── 03_dashboard_reporting_queries.sql
├── src/
│   ├── __init__.py
│   ├── main.py                    # Application bootstrap & CLI entrypoint
│   ├── common/                    # Core utilities and shared definitions
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic Settings loader
│   │   ├── logger.py              # Structured logging configuration
│   │   └── exceptions.py          # Custom domain exceptions
│   ├── domain/                    # Pure Domain Layer (Entities & Rules)
│   │   ├── __init__.py
│   │   ├── models.py              # Core entities (Device, Incident, Telemetry)
│   │   ├── diagnostic_report.py   # Parsed Cisco diagnostic data structures
│   │   └── rca_rules.py           # Pure rule evaluation logic & catalog
│   ├── ports/                     # Hexagonal Boundary Interfaces
│   │   ├── __init__.py
│   │   ├── ingestion.py           # EventIngestionPort Protocol
│   │   ├── repository.py          # IncidentRepositoryPort Protocol
│   │   └── llm_provider.py        # LLMProviderPort Protocol
│   ├── adapters/                  # Pluggable Inbound & Outbound Adapters
│   │   ├── __init__.py
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── synthetic_adapter.py    # Reads from synthetic generator
│   │   │   └── m365_graph_stub.py      # Future production Graph API connector stub
│   │   ├── repository/
│   │   │   ├── __init__.py
│   │   │   └── local_delta_repo.py     # Local file/parquet/delta repository
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── mock_provider.py        # Offline deterministic template generator
│   │       └── openai_provider.py      # OpenAI/Azure/Ollama compatible provider
│   ├── parsers/                   # Cisco CLI Multi-Command Parsing Engine
│   │   ├── __init__.py
│   │   ├── cisco_parser.py        # Master dispatcher
│   │   ├── interface_parser.py    # `show interfaces`
│   │   ├── transceiver_parser.py  # `show interfaces transceiver detail`
│   │   ├── environment_parser.py  # `show env power` & `show env temp`
│   │   ├── process_parser.py      # `show processes cpu` & `show processes mem`
│   │   └── syslog_parser.py       # Syslog regex normalizer
│   ├── correlation/               # Event Correlation & Sliding Window Engine
│   │   ├── __init__.py
│   │   ├── correlator.py          # Temporal sliding window manager
│   │   └── incident_manager.py    # Incident state machine
│   ├── ml/                        # Predictive Analytics & Risk Engine
│   │   ├── __init__.py
│   │   ├── features.py            # Rolling telemetry feature pipeline
│   │   ├── model.py               # Random Forest failure classifier
│   │   └── risk_scorer.py         # Composite 0-100 risk scoring & Top 10 ranker
│   ├── metrics/                   # Operations & Management KPI Engine
│   │   ├── __init__.py
│   │   └── kpi_calculator.py      # MTTA, MTTD, MTTR, Automation rate math
│   └── synthetic/                 # High-Fidelity Synthetic Simulation Engine
│       ├── __init__.py
│       ├── generator.py           # Master synthetic scenario coordinator
│       ├── device_factory.py      # Cisco device inventory synthesizer
│       ├── telemetry_factory.py   # Time-series telemetry synthesizer
│       └── cli_factory.py         # Cisco raw CLI string synthesizer
├── tests/
│   ├── conftest.py                # Pytest fixtures and mock objects
│   ├── unit/
│   │   ├── test_cisco_parsers.py  # Command parsing unit tests
│   │   ├── test_rca_rules.py      # Rule evaluation & citation unit tests
│   │   ├── test_correlation.py    # Sliding window correlation tests
│   │   ├── test_risk_scoring.py   # Composite scoring & ranking tests
│   │   └── test_metrics.py        # KPI mathematical accuracy tests
│   ├── integration/
│   │   ├── test_pipeline_e2e.py   # End-to-end incident ingestion to RCA
│   │   └── test_synthetic_data.py # Synthetic generator fidelity tests
│   └── golden_samples/            # Verified CLI command text files
│       ├── c9300_show_interfaces.txt
│       ├── c9500_show_transceiver.txt
│       ├── isr4451_show_env.txt
│       └── nx9k_show_processes.txt
├── .gitignore
├── .env.example                   # Template environment variables (no secrets)
├── pyproject.toml                 # Poetry/Hatch/Pip dependency specification
├── ruff.toml                      # Linter & formatter configuration
└── README.md                      # Platform quickstart & architecture overview
```

---

## 2. Module Responsibilities Matrix

| Module Path | Layer | Responsibility | Dependencies |
|---|---|---|---|
| `src/domain/` | Domain | Pure entities, typed data classes, RCA rules. | Zero external dependencies (Standard library only). |
| `src/ports/` | Domain Boundary | Abstract interfaces (`typing.Protocol`) for I/O. | `src/domain/` |
| `src/parsers/` | Application / Core | Translates unstructured CLI text into domain structures. | `src/domain/` |
| `src/correlation/` | Application | Pairs alerts, recoveries, and logs across time. | `src/domain/`, `src/parsers/` |
| `src/ml/` | ML / Analytics | Feature engineering, Random Forest inference, risk scoring. | `src/domain/`, `scikit-learn`, `pandas` |
| `src/adapters/` | Infrastructure | Implementations of ports (Synthetic, OpenAI, Storage). | `src/ports/`, external libraries |
| `src/synthetic/` | Tooling / Sim | High-fidelity generation of realistic Cisco data. | `src/domain/` |
| `src/metrics/` | Domain / App | Calculates MTTA, MTTD, MTTR, automation rates. | `src/domain/` |
