"""Health check endpoint and system status."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings

router = APIRouter(tags=["System"])


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="healthy", json_schema_extra={"example": "healthy"})
    app_name: str
    environment: str
    version: str = "0.1.0"
    timestamp: datetime
    is_synthetic: bool = True
    active_components: dict[str, str] = Field(default_factory=dict)


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return platform operational health status."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        environment=settings.app_env.value,
        version="0.1.0",
        timestamp=datetime.now(UTC),
        is_synthetic=True,
        active_components={
            "ingestion": "operational",
            "correlation": "operational",
            "rca": "operational",
            "prediction": "operational",
            "knowledge": "operational",
        },
    )
