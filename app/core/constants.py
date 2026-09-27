"""Application-wide constants, enumerations, and metadata definitions."""

from enum import StrEnum


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class IncidentState(StrEnum):
    ALERT_RECEIVED = "ALERT_RECEIVED"
    RECOVERY_RECEIVED = "RECOVERY_RECEIVED"
    DIAGNOSTICS_ATTACHED = "DIAGNOSTICS_ATTACHED"
    RCA_IN_PROGRESS = "RCA_IN_PROGRESS"
    RCA_COMPLETE = "RCA_COMPLETE"
    RESOLVED = "RESOLVED"
    UNRECOVERED_ALERT = "UNRECOVERED_ALERT"
    ORPHAN_DIAGNOSTIC = "ORPHAN_DIAGNOSTIC"


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    WARNING = "WARNING"
    INFO = "INFO"


class RiskCategory(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LLMProviderType(StrEnum):
    MOCK = "mock"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
