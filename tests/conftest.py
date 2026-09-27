"""Pytest fixtures for platform test suites."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated test configuration."""
    return Settings(
        app_name="network-operations-intelligence-test",
        debug=True,
        simulation_seed=42,
        default_correlation_window_minutes=60,
    )


@pytest.fixture
def client() -> TestClient:
    """Provide FastAPI test client."""
    app = create_app()
    return TestClient(app)
