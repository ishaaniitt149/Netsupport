"""LLM layer data contracts.

These models carry structured data *into* the LLM layer and structured data
*out* of it.  They are deliberately separate from the core domain models so
that changes to the LLM integration never break domain logic.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LLMTask(str, Enum):
    INCIDENT_SUMMARY = "incident_summary"
    RCA_EXPLANATION = "rca_explanation"
    TROUBLESHOOTING_SUMMARY = "troubleshooting_summary"
    KB_DRAFT = "kb_draft"
    PREVENTIVE_ACTION = "preventive_action"


class LLMContext(BaseModel):
    """All grounding data passed to the LLM.

    Nothing in this payload may be invented; every field must come from
    upstream deterministic components (correlation engine, RCA engine,
    diagnostic parser, resolution service).
    """

    task: LLMTask

    # ── Incident metadata ───────────────────────────────────────────────────
    incident_id: str
    device_id: str
    alert_type: str
    severity: str
    start_time: datetime
    recovery_time: datetime | None = None
    duration_minutes: float | None = None

    # ── RCA engine output ──────────────────────────────────────────────────
    probable_rca: str
    rca_confidence: float
    rca_rule_id: str
    rca_evidence: dict[str, str] = Field(default_factory=dict)
    raw_command_output: str | None = None
    rca_recommended_checks: list[str] = Field(default_factory=list)

    # ── Diagnostic parser output ───────────────────────────────────────────
    cpu_utilization: float | None = None
    memory_utilization: float | None = None
    packet_loss: float | None = None
    crc_errors: int | None = None
    input_errors: int | None = None
    output_errors: int | None = None
    interface_flaps: int | None = None
    interface_status: str | None = None
    bgp_status: str | None = None
    ospf_status: str | None = None
    temperature: float | None = None

    # ── Resolution history ─────────────────────────────────────────────────
    root_cause: str | None = None
    resolution_action: str | None = None
    validation_action: str | None = None
    resolved_by: str | None = None
    resolution_duration_minutes: float | None = None
    first_time_resolution: bool | None = None


class LLMResponse(BaseModel):
    """Output from the LLM layer."""

    task: LLMTask
    incident_id: str
    content: str
    model_used: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    grounded: bool = True  # Always True — enforced by prompt contract
