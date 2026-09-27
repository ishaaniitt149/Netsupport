"""Base domain models and common schema mixins."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


def get_utc_now() -> datetime:
    """Generate timezone-aware UTC datetime."""
    return datetime.now(UTC)


class PlatformBaseModel(BaseModel):
    """Base model for all network operations intelligence domain entities."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )

    is_synthetic: bool = Field(
        default=True,
        description="Explicit flag identifying synthetic simulation data versus real enterprise data.",
    )


class TimestampedModel(PlatformBaseModel):
    """Base model providing created_at and updated_at metadata."""

    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
