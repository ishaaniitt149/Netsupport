"""Knowledge base and SOP article management interface."""

from typing import Protocol

from app.models.kb import KBSOPArticle


class KnowledgeBasePort(Protocol):
    """Hexagonal Port: Version-controlled Standard Operating Procedure repository."""

    def get_article(self, doc_id: str) -> KBSOPArticle | None:
        """Retrieve an approved SOP article by identifier."""
        ...

    def save_article(self, article: KBSOPArticle) -> None:
        """Persist a newly drafted or updated SOP article."""
        ...

    def search_similar(self, query: str, limit: int = 5) -> list[KBSOPArticle]:
        """Find matching SOP articles based on symptoms and category."""
        ...
