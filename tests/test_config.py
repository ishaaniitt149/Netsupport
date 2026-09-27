"""Tests for configuration management and environment variable parsing."""

from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.constants import LLMProviderType


def test_default_settings() -> None:
    """Verify default configuration values."""
    settings = Settings()
    assert settings.app_name == "network-operations-intelligence"
    assert settings.app_port == 8000
    assert settings.simulation_seed == 42
    assert settings.llm_provider == LLMProviderType.MOCK
    assert settings.llm_temperature == 0.0


def test_yaml_config_loading() -> None:
    """Verify loading settings from configs/app.yaml."""
    yaml_path = Path("configs/app.yaml")
    assert yaml_path.exists(), "configs/app.yaml must exist"

    settings = Settings.load_from_yaml(yaml_path)
    assert settings.app_name == "network-operations-intelligence"
    assert settings.default_correlation_window_minutes == 60
    assert settings.optical_rx_low_alarm_dbm == -14.0
    assert settings.crc_error_spike_threshold == 100


def test_singleton_get_settings() -> None:
    """Verify get_settings returns an active Settings instance."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.app_name == "network-operations-intelligence"
