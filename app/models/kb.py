"""Knowledge Base and Standard Operating Procedure (SOP) models."""



from app.models.base import TimestampedModel


class KBSOPArticle(TimestampedModel):
    """Version-controlled Knowledge Base and Standard Operating Procedure article."""

    doc_id: str
    title: str
    category: str
    version: int = 1
    status: str = "DRAFT"  # DRAFT, UNDER_REVIEW, APPROVED, DEPRECATED
    markdown_content: str
    author: str = "NOIPMP-Grounded-LLM"
    reviewed_by: str | None = None
    reuse_count: int = 0
    matched_incident_count: int = 0
