"""Tests for health check endpoint and operational status."""

from fastapi.testclient import TestClient


def test_health_check_endpoint(client: TestClient) -> None:
    """Verify that /api/v1/health returns HTTP 200 and expected health metadata."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert data["is_synthetic"] is True
    assert "timestamp" in data
    assert "active_components" in data
    assert data["active_components"]["ingestion"] == "operational"
    assert data["active_components"]["rca"] == "operational"
