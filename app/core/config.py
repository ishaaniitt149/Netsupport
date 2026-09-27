"""Configuration management using Pydantic Settings and optional YAML file fallback."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import Environment, LLMProviderType


class RiskWeightsConfig(BaseSettings):
    ml_probability: float = 0.50
    vulnerability_penalty: float = 0.25
    telemetry_anomaly: float = 0.25


class RiskThresholdsConfig(BaseSettings):
    high: float = 70.0
    critical: float = 85.0


class Settings(BaseSettings):
    # Application Baseline
    app_name: str = "network-operations-intelligence"
    app_env: Environment = Environment.DEVELOPMENT
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    # Simulation & Synthetic Data
    simulation_seed: int = 42
    synthetic_device_count: int = 100
    default_correlation_window_minutes: int = 60

    # RCA Rule Thresholds
    optical_rx_low_alarm_dbm: float = -14.0
    crc_error_spike_threshold: int = 100
    cpu_critical_pct: float = 90.0
    memory_low_free_pct: float = 5.0

    # Predictive Settings
    lookback_days: int = 30
    forecast_horizon_days: int = 14
    risk_weights: RiskWeightsConfig = Field(default_factory=RiskWeightsConfig)
    risk_thresholds: RiskThresholdsConfig = Field(default_factory=RiskThresholdsConfig)

    # LLM Settings (Provider abstracted - zero secrets in code)
    llm_provider: LLMProviderType = LLMProviderType.MOCK
    llm_model_name: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_api_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_timeout_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @classmethod
    def load_from_yaml(cls, yaml_path: Path) -> "Settings":
        """Load settings with YAML file overrides."""
        if not yaml_path.exists():
            return cls()
        with open(yaml_path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        flat_data: dict[str, Any] = {}
        if "app" in data:
            flat_data["app_name"] = data["app"].get("name")
            flat_data["app_env"] = data["app"].get("environment")
            flat_data["app_host"] = data["app"].get("host")
            flat_data["app_port"] = data["app"].get("port")
            flat_data["debug"] = data["app"].get("debug")
        if "correlation" in data:
            flat_data["default_correlation_window_minutes"] = data["correlation"].get(
                "sliding_window_minutes"
            )
        if "rca" in data:
            flat_data["optical_rx_low_alarm_dbm"] = data["rca"].get("optical_rx_low_alarm_dbm")
            flat_data["crc_error_spike_threshold"] = data["rca"].get("crc_error_spike_threshold")
            flat_data["cpu_critical_pct"] = data["rca"].get("cpu_critical_pct")
            flat_data["memory_low_free_pct"] = data["rca"].get("memory_low_free_pct")
        if "llm" in data:
            flat_data["llm_provider"] = data["llm"].get("provider")
            flat_data["llm_model_name"] = data["llm"].get("model_name")
            flat_data["llm_temperature"] = data["llm"].get("temperature")
            flat_data["llm_timeout_seconds"] = data["llm"].get("timeout_seconds")

        # Clean out None values
        flat_data = {k: v for k, v in flat_data.items() if v is not None}
        return cls(**flat_data)


# Global settings singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Retrieve or initialize the global settings instance."""
    global _settings
    if _settings is None:
        yaml_config_path = Path("configs/app.yaml")
        if yaml_config_path.exists():
            _settings = Settings.load_from_yaml(yaml_config_path)
        else:
            _settings = Settings()
    return _settings
