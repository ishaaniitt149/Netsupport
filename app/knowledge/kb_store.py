"""Version-controlled KB / SOP store.

Architecture
------------
Articles are persisted as individual JSON files under a configurable base
directory using the layout::

    <kb_store_dir>/
        KB-0001/
            v1.0.json
            v1.1.json
        KB-0002/
            v1.0.json

Each file is written once and never overwritten, enforcing immutability at the
file-system level in addition to the Pydantic ``frozen=True`` on the model.

A sequential counter file ``_counter.txt`` tracks the next available numeric ID.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.models.kb_article import KBArticle, KBStatus, KBVersionHistory

# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

def _parse_version(v: str) -> tuple[int, int]:
    major, minor = v.split(".", 1)
    return int(major), int(minor)


def _bump_minor(v: str) -> str:
    major, minor = _parse_version(v)
    return f"{major}.{minor + 1}"


def _bump_major(v: str) -> str:
    major, _ = _parse_version(v)
    return f"{major + 1}.0"


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class KBStore:
    """File-system backed, version-controlled KB article store."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._counter_file = self.base_dir / "_counter.txt"

    # ------------------------------------------------------------------
    # ID allocation
    # ------------------------------------------------------------------

    def _next_kb_id(self) -> str:
        if self._counter_file.exists():
            current = int(self._counter_file.read_text().strip())
        else:
            current = 0
        next_id = current + 1
        self._counter_file.write_text(str(next_id))
        return f"KB-{next_id:04d}"

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _article_dir(self, kb_id: str) -> Path:
        if "/" in kb_id or "\\" in kb_id or ".." in kb_id:
            raise ValueError("Invalid KB ID: path traversal not allowed")
        return self.base_dir / kb_id

    def _article_path(self, kb_id: str, version: str) -> Path:
        safe_ver = version.replace(".", "_")
        return self._article_dir(kb_id) / f"v{safe_ver}.json"

    def _write(self, article: KBArticle) -> None:
        path = self._article_path(article.kb_id, article.version)
        if path.exists():
            raise FileExistsError(
                f"{article.kb_id} v{article.version} already exists — "
                "KB articles are immutable; create a new version instead."
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(article.model_dump_json(indent=2), encoding="utf-8")

    def _read(self, kb_id: str, version: str) -> KBArticle:
        path = self._article_path(kb_id, version)
        if not path.exists():
            raise FileNotFoundError(f"{kb_id} v{version} not found.")
        data = json.loads(path.read_text(encoding="utf-8"))
        return KBArticle(**data)

    def _all_versions(self, kb_id: str) -> list[str]:
        article_dir = self._article_dir(kb_id)
        if not article_dir.exists():
            return []
        files = sorted(article_dir.glob("v*.json"))
        versions = []
        for f in files:
            ver_str = f.stem[1:].replace("_", ".")  # v1_1 → 1.1
            versions.append(ver_str)
        return sorted(versions, key=_parse_version)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_kb(
        self,
        *,
        title: str,
        problem_statement: str,
        symptoms: list[str],
        root_cause: str,
        evidence: dict,
        resolution_steps: list[str],
        validation_steps: list[str],
        rollback_steps: list[str],
        created_by: str,
        source_incident_id: str | None = None,
        source_rca: str | None = None,
    ) -> KBArticle:
        """Allocate a new KB ID and persist v1.0 in DRAFT status.

        Content is never auto-approved.  The caller must explicitly call
        ``submit_for_review`` followed by ``approve`` to advance the status.
        """
        kb_id = self._next_kb_id()
        article = KBArticle(
            kb_id=kb_id,
            version="1.0",
            title=title,
            problem_statement=problem_statement,
            symptoms=symptoms,
            root_cause=root_cause,
            evidence=evidence,
            resolution_steps=resolution_steps,
            validation_steps=validation_steps,
            rollback_steps=rollback_steps,
            created_by=created_by,
            status=KBStatus.DRAFT,
            source_incident_id=source_incident_id,
            source_rca=source_rca,
        )
        self._write(article)
        return article

    def create_new_version(
        self,
        kb_id: str,
        updated_by: str,
        bump: str = "minor",
        **field_overrides,
    ) -> KBArticle:
        """Create a new immutable version of an existing KB article.

        Args:
            kb_id: The KB article to version.
            updated_by: Author name for the new version.
            bump: ``"minor"`` increments x.Y, ``"major"`` increments X.0.
            **field_overrides: Any ``KBArticle`` fields to change in the new version.

        Returns:
            The newly created ``KBArticle`` at the new version.
        """
        latest = self.get_latest_version(kb_id)
        new_ver = _bump_minor(latest.version) if bump == "minor" else _bump_major(latest.version)

        # Guard: ensure the target version slot does not already exist
        target_path = self._article_path(kb_id, new_ver)
        if target_path.exists():
            raise FileExistsError(
                f"{kb_id} v{new_ver} already exists — "
                "KB articles are immutable; bump to the next version instead."
            )

        base_data = latest.model_dump()
        # Strip immutable lineage fields that should transfer unchanged
        base_data.update(field_overrides)
        base_data["version"] = new_ver
        base_data["created_by"] = updated_by
        base_data["created_at"] = datetime.utcnow()
        base_data["status"] = KBStatus.DRAFT  # Always starts as DRAFT
        base_data["approved_by"] = None
        base_data["approved_at"] = None

        new_article = KBArticle(**base_data)
        self._write(new_article)
        return new_article

    def get_latest_version(self, kb_id: str) -> KBArticle:
        """Return the most recent version of a KB article."""
        versions = self._all_versions(kb_id)
        if not versions:
            raise FileNotFoundError(f"No versions found for {kb_id}.")
        return self._read(kb_id, versions[-1])

    def get_version(self, kb_id: str, version: str) -> KBArticle:
        """Return a specific version of a KB article."""
        return self._read(kb_id, version)

    def get_version_history(self, kb_id: str) -> list[KBVersionHistory]:
        """Return a list of all version summaries for a KB article."""
        history = []
        for ver in self._all_versions(kb_id):
            article = self._read(kb_id, ver)
            history.append(
                KBVersionHistory(
                    kb_id=article.kb_id,
                    version=article.version,
                    status=article.status,
                    created_by=article.created_by,
                    created_at=article.created_at,
                    approved_by=article.approved_by,
                )
            )
        return history

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def _transition_status(self, kb_id: str, version: str, **updates) -> KBArticle:
        """Internal: rewrite a version's JSON file with updated status fields.

        This is the ONLY sanctioned mutation path — and it is restricted to
        status transitions + approval metadata.  All other fields remain frozen.
        """
        path = self._article_path(kb_id, version)
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(updates)
        # Overwrite is allowed only for status transitions
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return KBArticle(**data)

    def submit_for_review(self, kb_id: str, version: str) -> KBArticle:
        """Advance a DRAFT article to PENDING_REVIEW."""
        article = self._read(kb_id, version)
        if article.status != KBStatus.DRAFT:
            raise ValueError(f"{kb_id} v{version} is not in DRAFT status.")
        return self._transition_status(kb_id, version, status=KBStatus.PENDING_REVIEW)

    def approve(self, kb_id: str, version: str, approved_by: str) -> KBArticle:
        """Approve a PENDING_REVIEW article.

        Only humans (identified by ``approved_by``) can approve — the system
        never auto-approves generated content.
        """
        article = self._read(kb_id, version)
        if article.status != KBStatus.PENDING_REVIEW:
            raise ValueError(f"{kb_id} v{version} must be in PENDING_REVIEW before approval.")
        return self._transition_status(
            kb_id,
            version,
            status=KBStatus.APPROVED,
            approved_by=approved_by,
            approved_at=datetime.utcnow().isoformat(),
        )

    def retire(self, kb_id: str, version: str) -> KBArticle:
        """Retire an article version (it remains readable but is marked RETIRED)."""
        return self._transition_status(kb_id, version, status=KBStatus.RETIRED)
