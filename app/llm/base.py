"""LLM provider abstraction interface."""

from typing import Protocol

from app.models.incident import Incident
from app.models.kb import KBSOPArticle
from app.models.rca import RCAResult


class LLMProviderPort(Protocol):
    """Hexagonal Port: Provider abstraction for grounded AI generation.

    Guarantees that LLMs are invoked strictly via contracts and cannot
    hallucinate technical evidence outside the provided citations.
    """

    def generate_incident_summary(self, incident: Incident, rca: RCAResult) -> str:
        """Synthesize a grounded 3-paragraph executive incident summary."""
        ...

    def draft_sop_article(self, incident: Incident, rca: RCAResult) -> KBSOPArticle:
        """Draft a structured, reproducible Standard Operating Procedure."""
        ...
