"""Root Cause Analysis (RCA) data structures and evidence citations."""

from datetime import datetime

from pydantic import Field

from app.models.base import TimestampedModel, get_utc_now


class EvidenceCitation(TimestampedModel):
    """Specific verifiable metric or syslog line supporting an RCA finding."""

    citation_id: str
    source_command: str
    parameter_name: str
    observed_value: str
    threshold_value: str | None = None
    description: str


class RCAResult(TimestampedModel):
    """Deterministic and explainable root cause evaluation result."""

    rca_id: str
    incident_id: str
    device_hostname: str
    matched_rule_id: str
    category: str
    probable_cause: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_citations: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    llm_executive_summary: str | None = None
    evaluated_at: datetime = Field(default_factory=get_utc_now)
