"""Comprehensive tests for the KB store and draft generator."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.knowledge.kb_draft_generator import KBDraftGenerator
from app.knowledge.kb_store import KBStore
from app.models.kb_article import KBArticle, KBStatus
from app.models.resolution import Resolution
from app.rca.engine import RCAResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path: Path) -> KBStore:
    return KBStore(tmp_path / "kb_store")


@pytest.fixture
def sample_rca() -> RCAResult:
    return RCAResult(
        incident_id="INC-0001",
        probable_rca="Interface degradation",
        confidence=0.88,
        evidence={"crc_errors": "1450", "interface_flaps": "8", "bgp_status": "ESTABLISHED"},
        rule_id="RULE-001-INTERFACE-DEGRADATION",
        recommended_checks=["Clean fiber optics", "Replace SFP module"],
    )


@pytest.fixture
def sample_resolution() -> Resolution:
    now = datetime(2023, 6, 1, 10, 0)
    return Resolution(
        incident_id="INC-0001",
        device_id="DEV-001",
        root_cause="Faulty SFP transceiver",
        resolution_action="Replaced SFP on Gi0/1",
        validation_action="Confirmed zero CRC errors over 15 min",
        resolved_by="Alice Smith",
        resolution_timestamp=now,
        acknowledged_at=now,
        diagnosed_at=now,
        resolution_duration=45.0,
        first_time_resolution=True,
    )


# ---------------------------------------------------------------------------
# KBStore: create_kb
# ---------------------------------------------------------------------------

class TestCreateKB:
    def test_creates_v1_0_in_draft_status(self, store: KBStore):
        article = store.create_kb(
            title="Test Article",
            problem_statement="A test problem",
            symptoms=["Symptom A"],
            root_cause="Root cause A",
            evidence={"crc_errors": "1450"},
            resolution_steps=["Step 1"],
            validation_steps=["Validate 1"],
            rollback_steps=["Rollback 1"],
            created_by="tester",
        )
        assert article.version == "1.0"
        assert article.status == KBStatus.DRAFT
        assert article.approved_by is None

    def test_ids_are_sequential(self, store: KBStore):
        a1 = store.create_kb(title="T1", problem_statement="P", symptoms=[], root_cause="R",
                              evidence={}, resolution_steps=[], validation_steps=[],
                              rollback_steps=[], created_by="sys")
        a2 = store.create_kb(title="T2", problem_statement="P", symptoms=[], root_cause="R",
                              evidence={}, resolution_steps=[], validation_steps=[],
                              rollback_steps=[], created_by="sys")
        assert a1.kb_id == "KB-0001"
        assert a2.kb_id == "KB-0002"

    def test_article_is_frozen(self, store: KBStore):
        from pydantic import ValidationError
        article = store.create_kb(
            title="Frozen", problem_statement="P", symptoms=[], root_cause="R",
            evidence={}, resolution_steps=[], validation_steps=[],
            rollback_steps=[], created_by="sys"
        )
        # Pydantic V2 frozen models raise ValidationError on field assignment
        with pytest.raises((ValidationError, TypeError)):
            article.title = "Mutated"


# ---------------------------------------------------------------------------
# KBStore: versioning
# ---------------------------------------------------------------------------

class TestVersioning:
    def _base(self, store: KBStore) -> KBArticle:
        return store.create_kb(
            title="Base", problem_statement="P", symptoms=["S1"], root_cause="R",
            evidence={"k": "v"}, resolution_steps=["RS1"], validation_steps=["VS1"],
            rollback_steps=["RB1"], created_by="engineer-1"
        )

    def test_minor_version_bump(self, store: KBStore):
        base = self._base(store)
        v1_1 = store.create_new_version(base.kb_id, updated_by="engineer-2", bump="minor",
                                         title="Updated Title")
        assert v1_1.version == "1.1"
        assert v1_1.title == "Updated Title"
        assert v1_1.kb_id == base.kb_id

    def test_major_version_bump(self, store: KBStore):
        base = self._base(store)
        v2_0 = store.create_new_version(base.kb_id, updated_by="engineer-2", bump="major")
        assert v2_0.version == "2.0"

    def test_new_version_starts_as_draft(self, store: KBStore):
        base = self._base(store)
        v1_1 = store.create_new_version(base.kb_id, updated_by="eng", bump="minor")
        assert v1_1.status == KBStatus.DRAFT

    def test_old_version_remains_intact(self, store: KBStore):
        base = self._base(store)
        store.create_new_version(base.kb_id, updated_by="eng", bump="minor", title="New Title")
        original = store.get_version(base.kb_id, "1.0")
        assert original.title == "Base"  # unchanged

    def test_duplicate_version_raises(self, store: KBStore):
        base = self._base(store)
        v1_1 = store.create_new_version(base.kb_id, updated_by="eng", bump="minor")
        # Manually write the v1_1 file again to trigger the FileExistsError guard
        with pytest.raises(FileExistsError):
            store._write(v1_1)

    def test_get_latest_version_returns_highest(self, store: KBStore):
        base = self._base(store)
        store.create_new_version(base.kb_id, updated_by="eng", bump="minor")
        store.create_new_version(base.kb_id, updated_by="eng", bump="minor")
        latest = store.get_latest_version(base.kb_id)
        assert latest.version == "1.2"

    def test_get_version_history_ordered(self, store: KBStore):
        base = self._base(store)
        store.create_new_version(base.kb_id, updated_by="eng", bump="minor")
        store.create_new_version(base.kb_id, updated_by="eng", bump="minor")
        history = store.get_version_history(base.kb_id)
        assert [h.version for h in history] == ["1.0", "1.1", "1.2"]


# ---------------------------------------------------------------------------
# KBStore: status transitions
# ---------------------------------------------------------------------------

class TestStatusTransitions:
    def _draft(self, store: KBStore) -> KBArticle:
        return store.create_kb(
            title="T", problem_statement="P", symptoms=[], root_cause="R",
            evidence={}, resolution_steps=[], validation_steps=[],
            rollback_steps=[], created_by="sys"
        )

    def test_draft_to_pending_review(self, store: KBStore):
        art = self._draft(store)
        updated = store.submit_for_review(art.kb_id, art.version)
        assert updated.status == KBStatus.PENDING_REVIEW

    def test_pending_review_to_approved(self, store: KBStore):
        art = self._draft(store)
        store.submit_for_review(art.kb_id, art.version)
        approved = store.approve(art.kb_id, art.version, approved_by="Jane Approver")
        assert approved.status == KBStatus.APPROVED
        assert approved.approved_by == "Jane Approver"

    def test_cannot_approve_draft_directly(self, store: KBStore):
        art = self._draft(store)
        with pytest.raises(ValueError, match="PENDING_REVIEW"):
            store.approve(art.kb_id, art.version, approved_by="Jane")

    def test_cannot_submit_already_pending(self, store: KBStore):
        art = self._draft(store)
        store.submit_for_review(art.kb_id, art.version)
        with pytest.raises(ValueError, match="DRAFT"):
            store.submit_for_review(art.kb_id, art.version)

    def test_retire_approved_article(self, store: KBStore):
        art = self._draft(store)
        store.submit_for_review(art.kb_id, art.version)
        store.approve(art.kb_id, art.version, approved_by="Jane")
        retired = store.retire(art.kb_id, art.version)
        assert retired.status == KBStatus.RETIRED


# ---------------------------------------------------------------------------
# Draft Generator
# ---------------------------------------------------------------------------

class TestKBDraftGenerator:
    def test_generates_draft_from_rca_only(self, store: KBStore, sample_rca: RCAResult):
        gen = KBDraftGenerator(store)
        article = gen.generate_draft(rca_result=sample_rca, created_by="sys")

        assert article.status == KBStatus.DRAFT
        assert article.approved_by is None
        assert "Interface degradation" in article.title
        assert article.source_incident_id == "INC-0001"
        assert article.source_rca == "RULE-001-INTERFACE-DEGRADATION"
        assert article.evidence == sample_rca.evidence
        assert "crc_errors=1450" in article.problem_statement

    def test_generates_draft_with_resolution(
        self, store: KBStore, sample_rca: RCAResult, sample_resolution: Resolution
    ):
        gen = KBDraftGenerator(store)
        article = gen.generate_draft(
            rca_result=sample_rca, resolution=sample_resolution, created_by="eng-1"
        )
        # Resolution action should appear in resolution steps
        assert any("Replaced SFP on Gi0/1" in step for step in article.resolution_steps)

    def test_draft_is_never_auto_approved(self, store: KBStore, sample_rca: RCAResult):
        gen = KBDraftGenerator(store)
        article = gen.generate_draft(rca_result=sample_rca)
        assert article.status == KBStatus.DRAFT
        assert article.approved_by is None

    def test_evidence_only_from_observed_data(self, store: KBStore, sample_rca: RCAResult):
        gen = KBDraftGenerator(store)
        article = gen.generate_draft(rca_result=sample_rca)
        # Evidence dict must exactly match what was in the RCA result — nothing invented
        assert article.evidence == sample_rca.evidence
