"""Version-controlled Knowledge Base / SOP models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class KBStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"


class KBArticle(BaseModel):
    """A single immutable version of a KB / SOP article.

    Once persisted, a ``KBArticle`` must never be mutated in-place.
    Corrections are represented as new minor/major version entries.
    """

    kb_id: str = Field(..., description="Base identifier shared across all versions, e.g. KB-0047")
    version: str = Field(..., description="Semantic version string, e.g. 1.0, 1.1, 2.0")
    title: str
    problem_statement: str
    symptoms: list[str]
    root_cause: str
    evidence: dict = Field(default_factory=dict, description="Key/value evidence pairs from diagnostics")
    resolution_steps: list[str]
    validation_steps: list[str]
    rollback_steps: list[str]
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: KBStatus = KBStatus.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None

    # Lineage
    source_incident_id: str | None = None
    source_rca: str | None = None

    model_config = ConfigDict(frozen=True)  # Enforce immutability once created


class KBVersionHistory(BaseModel):
    """Summary entry in the version history list."""

    kb_id: str
    version: str
    status: KBStatus
    created_by: str
    created_at: datetime
    approved_by: str | None = None
