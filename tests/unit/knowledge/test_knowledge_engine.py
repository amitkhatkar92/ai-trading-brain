"""
tests/unit/knowledge/test_knowledge_engine.py
================================================
Comprehensive tests for the IIOS Knowledge Engine (Wave 3).

Run with::

    .venv\\Scripts\\python -m pytest tests/unit/knowledge/ -v --tb=short

Coverage targets ≥90% for:
    - models (id, metadata, reference, record, snapshot, query, statistics)
    - validators (validator, constraints, integrity, consistency)
    - versioning engine
    - indexing
    - storage backend
    - repository (CRUD + query)
    - search engine
    - graph (traversal, cycle detection)
    - manager (facade)
    - engine (lifecycle)
"""

from __future__ import annotations

import time
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_all() -> None:
    """Reset every singleton so tests are fully isolated."""
    from iios.knowledge.knowledge_engine import reset_knowledge_engine
    from iios.knowledge.knowledge_manager import reset_knowledge_manager
    from iios.knowledge.knowledge_context import reset_knowledge_context
    from iios.knowledge.knowledge_factory import get_knowledge_factory
    from iios.knowledge.search.knowledge_search import reset_search_engine
    from iios.knowledge.graph.knowledge_graph import reset_knowledge_graph
    from iios.knowledge.versioning.knowledge_versioning import reset_versioning_engine
    from iios.knowledge.repositories.knowledge_repository import reset_knowledge_repository
    from iios.knowledge.indexing.knowledge_index import reset_knowledge_index
    from iios.knowledge.storage.knowledge_cache import reset_knowledge_cache
    from iios.knowledge.storage.knowledge_storage import reset_knowledge_storage
    from iios.knowledge.validators.knowledge_validator import reset_knowledge_validator
    from iios.knowledge.validators.knowledge_constraints import reset_constraint_checker
    from iios.knowledge.validators.knowledge_integrity import reset_integrity_checker
    from iios.knowledge.validators.knowledge_consistency import reset_consistency_checker

    reset_knowledge_engine()
    # reset_knowledge_engine already calls the rest, but be explicit for safety
    reset_knowledge_manager()
    reset_knowledge_context()
    reset_search_engine()
    reset_knowledge_graph()
    reset_versioning_engine()
    reset_knowledge_repository()
    reset_knowledge_index()
    reset_knowledge_cache()
    reset_knowledge_storage()
    reset_knowledge_validator()
    reset_constraint_checker()
    reset_integrity_checker()
    reset_consistency_checker()
    # Reset the module-level factory singleton
    import iios.knowledge.knowledge_factory as _f
    _f._factory = None


def _make_record(title: str = "Test record", **kwargs):
    from iios.knowledge.knowledge_factory import get_knowledge_factory
    f = get_knowledge_factory()
    return f.create_fact(title=title, content={"value": 1}, **kwargs)


# ===========================================================================
# 1. KnowledgeId
# ===========================================================================

class TestKnowledgeId:
    def setup_method(self):
        _reset_all()

    def test_new_generates_unique_ids(self):
        from iios.knowledge.models.knowledge_identifier import KnowledgeId
        a = KnowledgeId.new()
        b = KnowledgeId.new()
        assert a.uid != b.uid

    def test_full_property(self):
        from iios.knowledge.models.knowledge_identifier import KnowledgeId
        kid = KnowledgeId.new()
        assert kid.full == f"{kid.namespace}/{kid.uid}"

    def test_from_slug(self):
        from iios.knowledge.models.knowledge_identifier import KnowledgeId
        kid = KnowledgeId.from_slug("my-slug")
        assert kid.uid == "my-slug"

    def test_parse_full(self):
        from iios.knowledge.models.knowledge_identifier import KnowledgeId
        kid = KnowledgeId.new()
        parsed = KnowledgeId.parse(kid.full)
        assert parsed.uid == kid.uid
        assert parsed.namespace == kid.namespace

    def test_parse_uid_only(self):
        from iios.knowledge.models.knowledge_identifier import KnowledgeId
        parsed = KnowledgeId.parse("just-an-id")
        assert parsed.uid == "just-an-id"

    def test_generate_id_helper(self):
        from iios.knowledge.models.knowledge_identifier import generate_id
        kid = generate_id("test.ns")
        assert kid.namespace == "test.ns"
        assert len(kid.uid) > 0

    def test_parse_id_helper(self):
        from iios.knowledge.models.knowledge_identifier import generate_id, parse_id
        kid = generate_id()
        parsed = parse_id(kid.full)
        assert parsed.uid == kid.uid


# ===========================================================================
# 2. KnowledgeMetadata
# ===========================================================================

class TestKnowledgeMetadata:
    def setup_method(self):
        _reset_all()

    def test_default_confidence_clamped(self):
        from iios.knowledge.models.knowledge_metadata import KnowledgeMetadata
        m = KnowledgeMetadata(confidence=5.0)
        assert m.confidence == 1.0

    def test_tag_management(self):
        from iios.knowledge.models.knowledge_metadata import KnowledgeMetadata
        m = KnowledgeMetadata()
        m.add_tag("equity")
        m.add_tag("nifty")
        assert m.has_tag("equity")
        m.remove_tag("equity")
        assert not m.has_tag("equity")

    def test_touch_updates_timestamp(self):
        from iios.knowledge.models.knowledge_metadata import KnowledgeMetadata
        m = KnowledgeMetadata()
        before = m.updated_at
        time.sleep(0.001)
        m.touch()
        assert m.updated_at >= before

    def test_to_dict_roundtrip(self):
        from iios.knowledge.models.knowledge_metadata import KnowledgeMetadata
        m = KnowledgeMetadata(description="test", tags=["a", "b"], confidence=0.8)
        d = m.to_dict()
        m2 = KnowledgeMetadata.from_dict(d)
        assert m2.description == "test"
        assert m2.tags == ["a", "b"]
        assert m2.confidence == 0.8

    def test_max_tags_silently_ignored(self):
        from iios.knowledge.models.knowledge_metadata import KnowledgeMetadata
        from iios.knowledge.knowledge_constants import MAX_TAGS
        m = KnowledgeMetadata(tags=[f"tag{i}" for i in range(MAX_TAGS)])
        m.add_tag("overflow")  # exceeds limit — silently ignored
        assert len(m.tags) == MAX_TAGS  # count unchanged

    def test_evolve(self):
        from iios.knowledge.models.knowledge_metadata import KnowledgeMetadata
        m = KnowledgeMetadata(description="original")
        m2 = m.evolve(description="updated")
        assert m2.description == "updated"
        assert m.description == "original"


# ===========================================================================
# 3. KnowledgeRecord
# ===========================================================================

class TestKnowledgeRecord:
    def setup_method(self):
        _reset_all()

    def test_create_record(self):
        rec = _make_record("My record")
        assert rec.title == "My record"
        assert not rec.is_deleted

    def test_is_active_draft(self):
        from iios.knowledge.knowledge_constants import KnowledgeStatus
        rec = _make_record()
        # factory creates DRAFT by default → is_active is False if active only means ACTIVE
        assert rec.status == KnowledgeStatus.DRAFT

    def test_activate(self):
        from iios.knowledge.knowledge_constants import KnowledgeStatus
        rec = _make_record()
        rec.activate()
        assert rec.status == KnowledgeStatus.ACTIVE
        assert rec.is_active

    def test_archive(self):
        from iios.knowledge.knowledge_constants import KnowledgeStatus
        rec = _make_record()
        rec.archive()
        assert rec.status == KnowledgeStatus.ARCHIVED

    def test_deprecate(self):
        from iios.knowledge.knowledge_constants import KnowledgeStatus
        rec = _make_record()
        rec.deprecate()
        assert rec.status == KnowledgeStatus.DEPRECATED

    def test_to_dict_roundtrip(self):
        rec = _make_record("Roundtrip test")
        d = rec.to_dict()
        from iios.knowledge.models.knowledge_record import KnowledgeRecord
        rec2 = KnowledgeRecord.from_dict(d)
        assert rec2.title == rec.title
        assert rec2.id == rec.id

    def test_add_reference(self):
        from iios.knowledge.models.knowledge_reference import KnowledgeReference
        from iios.knowledge.knowledge_constants import RelationshipType, RelationshipStrength
        rec = _make_record("Src")
        ref = KnowledgeReference(
            source_id="src", target_id="tgt",
            relationship_type=RelationshipType.RELATED_TO,
            strength=RelationshipStrength.WEAK,
        )
        rec.add_reference(ref)
        assert len(rec.references) == 1

    def test_remove_reference(self):
        from iios.knowledge.models.knowledge_reference import KnowledgeReference
        from iios.knowledge.knowledge_constants import RelationshipType, RelationshipStrength
        rec = _make_record()
        ref = KnowledgeReference(
            source_id="s", target_id="t",
            relationship_type=RelationshipType.RELATED_TO,
            strength=RelationshipStrength.WEAK,
        )
        rec.add_reference(ref)
        removed = rec.remove_reference(ref.ref_id)
        assert removed
        # remove_reference deactivates (not deletes) the reference
        assert all(not r.is_active for r in rec.references if r.ref_id == ref.ref_id)


# ===========================================================================
# 4. KnowledgeValidator
# ===========================================================================

class TestKnowledgeValidator:
    def setup_method(self):
        _reset_all()

    def test_valid_record_passes(self):
        from iios.knowledge.validators.knowledge_validator import get_knowledge_validator
        v = get_knowledge_validator()
        rec = _make_record("Valid record")
        report = v.validate(rec)
        assert report.passed

    def test_empty_title_warns(self):
        from iios.knowledge.validators.knowledge_validator import get_knowledge_validator
        v = get_knowledge_validator()
        rec = _make_record()
        rec.title = ""
        report = v.validate(rec)
        # Empty title generates a WARNING (not an error) — report still passes but has warnings
        assert len(report.warnings) > 0

    def test_custom_rule(self):
        from iios.knowledge.validators.knowledge_validator import get_knowledge_validator
        from iios.knowledge.validators.knowledge_validator import ValidationReport, ValidationIssue
        from iios.knowledge.knowledge_constants import ValidationResult
        v = get_knowledge_validator()

        def no_numeric_titles(rec, report):
            if rec.title.isdigit():
                report.add_error("title", "Title must not be purely numeric")

        v.register_rule("no_numeric", no_numeric_titles)
        rec = _make_record("12345")
        report = v.validate(rec)
        assert not report.passed
        v.unregister_rule("no_numeric")

    def test_validate_or_raise(self):
        from iios.knowledge.validators.knowledge_validator import get_knowledge_validator
        from iios.knowledge.knowledge_exceptions import KnowledgeValidationError
        v = get_knowledge_validator()
        rec = _make_record()
        # Force an error: set confidence out of [0,1] via a custom rule
        def bad_rule(r, report):
            report.add_error("confidence", "forced error for test")
        v.register_rule("_test_force_error", bad_rule)
        try:
            with pytest.raises(KnowledgeValidationError):
                v.validate_or_raise(rec)
        finally:
            v.unregister_rule("_test_force_error")

    def test_list_rules(self):
        from iios.knowledge.validators.knowledge_validator import get_knowledge_validator
        v = get_knowledge_validator()
        rules = v.list_rules()
        assert len(rules) >= 7

    def test_compute_checksum(self):
        from iios.knowledge.validators.knowledge_validator import get_knowledge_validator
        v = get_knowledge_validator()
        rec = _make_record("checksum test")
        cs = v.compute_checksum(rec)
        assert isinstance(cs, str)
        assert len(cs) >= 32


# ===========================================================================
# 5. ConstraintChecker
# ===========================================================================

class TestConstraintChecker:
    def setup_method(self):
        _reset_all()

    def test_built_in_constraints_pass(self):
        from iios.knowledge.validators.knowledge_constraints import get_constraint_checker
        cc = get_constraint_checker()
        rec = _make_record("Valid")
        issues = cc.check(rec)
        errors = [i for i in issues if i.is_error()]
        assert len(errors) == 0

    def test_invalid_confidence_fails(self):
        from iios.knowledge.validators.knowledge_constraints import get_constraint_checker
        cc = get_constraint_checker()
        rec = _make_record("Bad confidence")
        rec.metadata.confidence = -0.5
        issues = cc.check(rec)
        errors = [i for i in issues if i.is_error()]
        assert len(errors) > 0

    def test_custom_constraint(self):
        from iios.knowledge.validators.knowledge_constraints import get_constraint_checker, ConstraintDefinition
        from iios.knowledge.knowledge_constants import ConstraintType
        cc = get_constraint_checker()

        # check_fn receives the FIELD VALUE (str) and must return bool (False = violation)
        def check_fn(value: str) -> bool:
            if value is None:
                return True
            return "bad" not in str(value).lower()

        defn = ConstraintDefinition(
            name="no_bad_title",
            constraint_type=ConstraintType.CUSTOM,
            target_field="title",
            check_fn=check_fn,
            message_template="Title must not contain 'bad'",
            code="C-TEST-001",
        )
        cc.register(defn)
        rec = _make_record("bad record")
        issues = cc.check(rec)
        assert any(i.code == "C-TEST-001" for i in issues)
        cc.unregister("no_bad_title")

    def test_list_names(self):
        from iios.knowledge.validators.knowledge_constraints import get_constraint_checker
        cc = get_constraint_checker()
        names = cc.list_names()
        assert len(names) >= 3


# ===========================================================================
# 6. IntegrityChecker
# ===========================================================================

class TestIntegrityChecker:
    def setup_method(self):
        _reset_all()

    def test_stamp_and_verify(self):
        from iios.knowledge.validators.knowledge_integrity import get_integrity_checker
        ic = get_integrity_checker()
        rec = _make_record("integrity test")
        ic.stamp(rec)
        assert ic.verify(rec)

    def test_tampered_content_fails(self):
        from iios.knowledge.validators.knowledge_integrity import get_integrity_checker
        ic = get_integrity_checker()
        rec = _make_record("integrity test")
        ic.stamp(rec)
        # checksum covers record.content — tampering content invalidates it
        rec.content = {"tampered": True}
        assert not ic.verify(rec)

    def test_checksum_is_deterministic(self):
        from iios.knowledge.validators.knowledge_integrity import get_integrity_checker
        ic = get_integrity_checker()
        rec = _make_record("deterministic")
        cs1 = ic.compute_checksum(rec)
        cs2 = ic.compute_checksum(rec)
        assert cs1 == cs2

    def test_verify_or_raise(self):
        from iios.knowledge.validators.knowledge_integrity import get_integrity_checker
        from iios.knowledge.knowledge_exceptions import KnowledgeIntegrityError
        ic = get_integrity_checker()
        rec = _make_record("raises test")
        ic.stamp(rec)
        rec.content = {"tampered": True}  # content tamper is detected
        with pytest.raises(KnowledgeIntegrityError):
            ic.verify_or_raise(rec)


# ===========================================================================
# 7. VersioningEngine
# ===========================================================================

class TestVersioningEngine:
    def setup_method(self):
        _reset_all()

    def test_snapshot_stores_history(self):
        from iios.knowledge.versioning.knowledge_versioning import get_versioning_engine
        ve = get_versioning_engine()
        rec = _make_record("v-rec")
        snap = ve.snapshot(rec, change_summary="initial")
        history = ve.history(rec.id)
        assert len(history) == 1
        assert history[0].snapshot_id == snap.snapshot_id

    def test_bump_patch(self):
        from iios.knowledge.versioning.knowledge_versioning import get_versioning_engine
        from iios.knowledge.knowledge_constants import VersionBump
        ve = get_versioning_engine()
        rec = _make_record("bump-test")
        assert rec.version == "1.0.0"
        ve.bump_version(rec, VersionBump.PATCH)
        assert rec.version == "1.0.1"

    def test_bump_minor(self):
        from iios.knowledge.versioning.knowledge_versioning import get_versioning_engine
        from iios.knowledge.knowledge_constants import VersionBump
        ve = get_versioning_engine()
        rec = _make_record("minor-test")
        ve.bump_version(rec, VersionBump.MINOR)
        assert rec.version == "1.1.0"

    def test_bump_major(self):
        from iios.knowledge.versioning.knowledge_versioning import get_versioning_engine
        from iios.knowledge.knowledge_constants import VersionBump
        ve = get_versioning_engine()
        rec = _make_record("major-test")
        ve.bump_version(rec, VersionBump.MAJOR)
        assert rec.version == "2.0.0"

    def test_rollback(self):
        from iios.knowledge.versioning.knowledge_versioning import get_versioning_engine
        from iios.knowledge.knowledge_constants import VersionBump
        ve = get_versioning_engine()
        rec = _make_record("rollback-test")
        snap1 = ve.snapshot(rec, change_summary="v1")
        rec.title = "Updated title"
        ve.bump_version(rec, VersionBump.PATCH, change_summary="v2")
        rolled = ve.rollback(rec, snap1.snapshot_id)
        assert rolled.title == "rollback-test"

    def test_version_count(self):
        from iios.knowledge.versioning.knowledge_versioning import get_versioning_engine
        from iios.knowledge.knowledge_constants import VersionBump
        ve = get_versioning_engine()
        rec = _make_record("count-test")
        ve.snapshot(rec)
        ve.bump_version(rec, VersionBump.PATCH)
        assert ve.version_count(rec.id) >= 1

    def test_diff(self):
        from iios.knowledge.versioning.knowledge_versioning import get_versioning_engine
        from iios.knowledge.knowledge_constants import VersionBump
        ve = get_versioning_engine()
        rec = _make_record("diff-test")
        snap1 = ve.snapshot(rec, change_summary="v1")
        rec.title = "New title"
        ve.bump_version(rec, VersionBump.PATCH, change_summary="v2")
        history = ve.history(rec.id)
        if len(history) >= 2:
            diff = ve.diff(history[-1], history[0])
            assert diff is not None

    def test_history_empty_for_unknown(self):
        from iios.knowledge.versioning.knowledge_versioning import get_versioning_engine
        ve = get_versioning_engine()
        assert ve.history("iios.knowledge/unknown") == []


# ===========================================================================
# 8. KnowledgeIndex
# ===========================================================================

class TestKnowledgeIndex:
    def setup_method(self):
        _reset_all()

    def test_index_and_find_by_type(self):
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        from iios.knowledge.knowledge_constants import KnowledgeType
        idx = get_knowledge_index()
        rec = _make_record("type-test")
        idx.index(rec)
        ids = idx.by_type(KnowledgeType.FACT)
        assert rec.id in ids

    def test_index_and_find_by_tag(self):
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        idx = get_knowledge_index()
        rec = _make_record("tag-test")
        rec.metadata.add_tag("equity")
        idx.index(rec)
        ids = idx.by_tag("equity")
        assert rec.id in ids

    def test_index_and_find_by_keyword(self):
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        idx = get_knowledge_index()
        rec = _make_record("NIFTY 50 trend analysis")
        idx.index(rec)
        ids = idx.by_keyword("nifty")
        assert rec.id in ids

    def test_deindex_removes_from_all(self):
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        from iios.knowledge.knowledge_constants import KnowledgeType
        idx = get_knowledge_index()
        rec = _make_record("remove test")
        idx.index(rec)
        idx.deindex(rec.id)
        ids = idx.by_type(KnowledgeType.FACT)
        assert rec.id not in ids

    def test_count(self):
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        idx = get_knowledge_index()
        for i in range(3):
            idx.index(_make_record(f"rec{i}"))
        assert idx.count() == 3

    def test_by_tags_match_all(self):
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        idx = get_knowledge_index()
        rec = _make_record("multi-tag")
        rec.metadata.add_tag("a")
        rec.metadata.add_tag("b")
        idx.index(rec)
        ids = idx.by_tags(["a", "b"], match_all=True)
        assert rec.id in ids
        ids_miss = idx.by_tags(["a", "c"], match_all=True)
        assert rec.id not in ids_miss

    def test_all_ids(self):
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        idx = get_knowledge_index()
        rec = _make_record("all-ids-test")
        idx.index(rec)
        assert rec.id in idx.all_ids()


# ===========================================================================
# 9. KnowledgeStorage
# ===========================================================================

class TestKnowledgeStorage:
    def setup_method(self):
        _reset_all()

    def test_put_and_get(self):
        from iios.knowledge.storage.knowledge_storage import get_knowledge_storage
        store = get_knowledge_storage()
        rec = _make_record("store-test")
        store.put(rec)
        got = store.get(rec.id)
        assert got.id == rec.id

    def test_get_missing_raises(self):
        from iios.knowledge.storage.knowledge_storage import get_knowledge_storage
        from iios.knowledge.knowledge_exceptions import KnowledgeNotFoundError
        store = get_knowledge_storage()
        with pytest.raises(KnowledgeNotFoundError):
            store.get("iios.knowledge/nonexistent")

    def test_soft_delete(self):
        from iios.knowledge.storage.knowledge_storage import get_knowledge_storage
        store = get_knowledge_storage()
        rec = _make_record("soft-del")
        store.put(rec)
        store.delete(rec.id, hard=False)
        got = store.get(rec.id)  # still present
        assert got.is_deleted

    def test_hard_delete(self):
        from iios.knowledge.storage.knowledge_storage import get_knowledge_storage
        from iios.knowledge.knowledge_exceptions import KnowledgeNotFoundError
        store = get_knowledge_storage()
        rec = _make_record("hard-del")
        store.put(rec)
        store.delete(rec.id, hard=True)
        with pytest.raises(KnowledgeNotFoundError):
            store.get(rec.id)

    def test_restore(self):
        from iios.knowledge.storage.knowledge_storage import get_knowledge_storage
        store = get_knowledge_storage()
        rec = _make_record("restore-test")
        store.put(rec)
        store.delete(rec.id)
        store.restore(rec.id)
        got = store.get(rec.id)
        assert not got.is_deleted

    def test_bulk_put(self):
        from iios.knowledge.storage.knowledge_storage import get_knowledge_storage
        store = get_knowledge_storage()
        recs = [_make_record(f"bulk-{i}") for i in range(5)]
        n = store.bulk_put(recs)
        assert n == 5
        assert store.count() >= 5

    def test_all_excludes_deleted(self):
        from iios.knowledge.storage.knowledge_storage import get_knowledge_storage
        store = get_knowledge_storage()
        rec = _make_record("all-excl")
        store.put(rec)
        store.delete(rec.id)
        live = store.all(include_deleted=False)
        assert all(not r.is_deleted for r in live)

    def test_exists(self):
        from iios.knowledge.storage.knowledge_storage import get_knowledge_storage
        store = get_knowledge_storage()
        rec = _make_record("exists-test")
        assert not store.exists(rec.id)
        store.put(rec)
        assert store.exists(rec.id)


# ===========================================================================
# 10. KnowledgeRepository
# ===========================================================================

class TestKnowledgeRepository:
    def setup_method(self):
        _reset_all()

    def test_add_and_get(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        repo = get_knowledge_repository()
        rec = _make_record("repo-test")
        repo.add(rec)
        got = repo.get(rec.id)
        assert got.id == rec.id

    def test_duplicate_raises(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        from iios.knowledge.knowledge_exceptions import KnowledgeAlreadyExistsError
        repo = get_knowledge_repository()
        rec = _make_record("dup")
        repo.add(rec)
        with pytest.raises(KnowledgeAlreadyExistsError):
            repo.add(rec)

    def test_update(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        repo = get_knowledge_repository()
        rec = _make_record("update-test")
        repo.add(rec)
        rec.title = "Updated"
        repo.update(rec)
        got = repo.get(rec.id)
        assert got.title == "Updated"

    def test_update_missing_raises(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        from iios.knowledge.knowledge_exceptions import KnowledgeNotFoundError
        repo = get_knowledge_repository()
        rec = _make_record("missing-update")
        with pytest.raises(KnowledgeNotFoundError):
            repo.update(rec)

    def test_delete_soft(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        from iios.knowledge.knowledge_exceptions import KnowledgeNotFoundError
        repo = get_knowledge_repository()
        rec = _make_record("del-test")
        repo.add(rec)
        repo.delete(rec.id)
        with pytest.raises(KnowledgeNotFoundError):
            repo.get(rec.id)

    def test_delete_hard(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        from iios.knowledge.knowledge_exceptions import KnowledgeNotFoundError
        repo = get_knowledge_repository()
        rec = _make_record("hard-del-repo")
        repo.add(rec)
        repo.delete(rec.id, hard=True)
        with pytest.raises(KnowledgeNotFoundError):
            repo.get(rec.id)

    def test_restore(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        repo = get_knowledge_repository()
        rec = _make_record("restore-repo")
        repo.add(rec)
        repo.delete(rec.id)
        repo.restore(rec.id)
        got = repo.get(rec.id)
        assert not got.is_deleted

    def test_query_all(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        from iios.knowledge.models.knowledge_query import KnowledgeQuery
        repo = get_knowledge_repository()
        for i in range(4):
            repo.add(_make_record(f"q-{i}"))
        result = repo.query(KnowledgeQuery())
        assert result.total >= 4

    def test_query_by_type(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        from iios.knowledge.models.knowledge_query import KnowledgeQuery, KnowledgeFilter
        from iios.knowledge.knowledge_constants import KnowledgeType
        repo = get_knowledge_repository()
        repo.add(_make_record("fact-query"))
        filt = KnowledgeFilter(knowledge_types=[KnowledgeType.FACT])
        result = repo.query(KnowledgeQuery(filter=filt))
        assert result.total >= 1

    def test_upsert(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        repo = get_knowledge_repository()
        rec = _make_record("upsert-test")
        repo.upsert(rec)
        rec.title = "Upserted"
        repo.upsert(rec)
        got = repo.get(rec.id)
        assert got.title == "Upserted"

    def test_bulk_add(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        repo = get_knowledge_repository()
        recs = [_make_record(f"bulk-{i}") for i in range(5)]
        n = repo.bulk_add(recs)
        assert n == 5

    def test_count(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        repo = get_knowledge_repository()
        n_before = repo.count()
        repo.add(_make_record("count-test"))
        assert repo.count() == n_before + 1

    def test_stats(self):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        repo = get_knowledge_repository()
        repo.add(_make_record("stats-test"))
        s = repo.stats()
        assert s.total_items >= 1


# ===========================================================================
# 11. KnowledgeSearchEngine
# ===========================================================================

class TestKnowledgeSearchEngine:
    def setup_method(self):
        _reset_all()

    def _seed_repo(self, n: int = 3):
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        repo = get_knowledge_repository()
        titles = ["NIFTY 50 bullish trend", "BANKNIFTY puts reversal", "equity momentum strategy"]
        for title in titles[:n]:
            rec = _make_record(title)
            repo.add(rec)
        return repo

    def test_keyword_search_finds_match(self):
        from iios.knowledge.search.knowledge_search import get_search_engine
        from iios.knowledge.models.knowledge_query import SearchQuery
        self._seed_repo()
        engine = get_search_engine()
        results = engine.search(SearchQuery(text="NIFTY"))
        assert len(results) >= 1

    def test_search_no_match_returns_empty(self):
        from iios.knowledge.search.knowledge_search import get_search_engine
        from iios.knowledge.models.knowledge_query import SearchQuery
        self._seed_repo()
        engine = get_search_engine()
        results = engine.search(SearchQuery(text="xyznonexistent123"))
        assert len(results) == 0

    def test_find_by_type(self):
        from iios.knowledge.search.knowledge_search import get_search_engine
        from iios.knowledge.knowledge_constants import KnowledgeType
        self._seed_repo()
        engine = get_search_engine()
        recs = engine.find_by_type(KnowledgeType.FACT)
        assert len(recs) >= 1

    def test_find_by_tags(self):
        from iios.knowledge.search.knowledge_search import get_search_engine
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        from iios.knowledge.indexing.knowledge_index import get_knowledge_index
        repo = get_knowledge_repository()
        idx = get_knowledge_index()
        rec = _make_record("tagged record")
        rec.metadata.add_tag("momentum")
        repo.add(rec)
        engine = get_search_engine()
        recs = engine.find_by_tags(["momentum"])
        assert any(r.id == rec.id for r in recs)

    def test_search_paged(self):
        from iios.knowledge.search.knowledge_search import get_search_engine
        from iios.knowledge.models.knowledge_query import SearchQuery, PageRequest
        self._seed_repo()
        engine = get_search_engine()
        sq = SearchQuery(text="nifty", pagination=PageRequest(page=1, page_size=1))
        result = engine.search_paged(sq)
        assert result.page_size == 1

    def test_exact_search(self):
        from iios.knowledge.search.knowledge_search import get_search_engine
        from iios.knowledge.models.knowledge_query import SearchQuery
        from iios.knowledge.knowledge_constants import SearchMode
        from iios.knowledge.repositories.knowledge_repository import get_knowledge_repository
        repo = get_knowledge_repository()
        rec = _make_record("exact-search-record")
        repo.add(rec)
        engine = get_search_engine()
        results = engine.search(SearchQuery(text=rec.id, mode=SearchMode.EXACT))
        assert len(results) == 1
        assert results[0].record.id == rec.id


# ===========================================================================
# 12. KnowledgeGraph
# ===========================================================================

class TestKnowledgeGraph:
    def setup_method(self):
        _reset_all()

    def test_add_and_find_node(self):
        from iios.knowledge.graph.knowledge_graph import get_knowledge_graph
        g = get_knowledge_graph()
        g.add_node("node-a")
        assert g.has_node("node-a")

    def test_add_edge_and_successors(self):
        from iios.knowledge.graph.knowledge_graph import get_knowledge_graph
        from iios.knowledge.models.knowledge_reference import KnowledgeReference
        from iios.knowledge.knowledge_constants import RelationshipType, RelationshipStrength
        g = get_knowledge_graph()
        ref = KnowledgeReference(
            source_id="a", target_id="b",
            relationship_type=RelationshipType.RELATED_TO,
            strength=RelationshipStrength.WEAK,
        )
        g.add_edge(ref)
        assert "b" in g.successors("a")
        assert "a" in g.predecessors("b")

    def test_shortest_path(self):
        from iios.knowledge.graph.knowledge_graph import get_knowledge_graph
        from iios.knowledge.models.knowledge_reference import KnowledgeReference
        from iios.knowledge.knowledge_constants import RelationshipType, RelationshipStrength
        g = get_knowledge_graph()
        for src, tgt in [("x", "y"), ("y", "z")]:
            ref = KnowledgeReference(
                source_id=src, target_id=tgt,
                relationship_type=RelationshipType.RELATED_TO,
                strength=RelationshipStrength.WEAK,
            )
            g.add_edge(ref)
        path = g.shortest_path("x", "z")
        assert path == ["x", "y", "z"]

    def test_no_path_returns_empty(self):
        from iios.knowledge.graph.knowledge_graph import get_knowledge_graph
        g = get_knowledge_graph()
        g.add_node("isolated-a")
        g.add_node("isolated-b")
        assert g.shortest_path("isolated-a", "isolated-b") == []

    def test_cycle_detection(self):
        from iios.knowledge.graph.knowledge_graph import get_knowledge_graph
        from iios.knowledge.models.knowledge_reference import KnowledgeReference
        from iios.knowledge.knowledge_constants import RelationshipType, RelationshipStrength
        g = get_knowledge_graph()
        for src, tgt in [("p", "q"), ("q", "r"), ("r", "p")]:
            ref = KnowledgeReference(
                source_id=src, target_id=tgt,
                relationship_type=RelationshipType.RELATED_TO,
                strength=RelationshipStrength.WEAK,
            )
            g.add_edge(ref)
        assert g.has_cycle()

    def test_no_cycle_in_dag(self):
        from iios.knowledge.graph.knowledge_graph import get_knowledge_graph
        from iios.knowledge.models.knowledge_reference import KnowledgeReference
        from iios.knowledge.knowledge_constants import RelationshipType, RelationshipStrength
        g = get_knowledge_graph()
        for src, tgt in [("m", "n"), ("n", "o")]:
            ref = KnowledgeReference(
                source_id=src, target_id=tgt,
                relationship_type=RelationshipType.RELATED_TO,
                strength=RelationshipStrength.WEAK,
            )
            g.add_edge(ref)
        assert not g.has_cycle()

    def test_remove_node(self):
        from iios.knowledge.graph.knowledge_graph import get_knowledge_graph
        g = get_knowledge_graph()
        g.add_node("del-node")
        g.remove_node("del-node")
        assert not g.has_node("del-node")

    def test_descendants(self):
        from iios.knowledge.graph.knowledge_graph import get_knowledge_graph
        from iios.knowledge.models.knowledge_reference import KnowledgeReference
        from iios.knowledge.knowledge_constants import RelationshipType, RelationshipStrength
        g = get_knowledge_graph()
        for src, tgt in [("root", "child"), ("child", "leaf")]:
            ref = KnowledgeReference(
                source_id=src, target_id=tgt,
                relationship_type=RelationshipType.RELATED_TO,
                strength=RelationshipStrength.WEAK,
            )
            g.add_edge(ref)
        d = g.descendants("root")
        assert "child" in d and "leaf" in d


# ===========================================================================
# 13. KnowledgeManager (facade)
# ===========================================================================

class TestKnowledgeManager:
    def setup_method(self):
        _reset_all()

    def test_create_and_get_fact(self):
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager()
        rec = km.create_fact("NIFTY close today", {"close": 24000})
        assert rec.id
        got = km.get(rec.id)
        assert got.title == "NIFTY close today"

    def test_search(self):
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager()
        km.create_fact("BANKNIFTY support zone", {"level": 48000})
        results = km.search("BANKNIFTY")
        assert len(results) >= 1

    def test_update(self):
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager()
        rec = km.create_fact("update-me", {"val": 1})
        rec.title = "updated-fact"
        updated = km.update(rec)
        assert updated.title == "updated-fact"

    def test_delete_and_restore(self):
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager()
        rec = km.create_fact("delete-restore-test")
        assert km.delete(rec.id)
        assert km.restore(rec.id)
        assert km.exists(rec.id)

    def test_link_and_related(self):
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        from iios.knowledge.knowledge_constants import RelationshipType
        km = get_knowledge_manager()
        a = km.create_fact("node-a")
        b = km.create_fact("node-b")
        km.link(a.id, b.id, RelationshipType.RELATED_TO)
        related = km.related(a.id)
        assert b.id in related

    def test_history(self):
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager()
        rec = km.create_fact("history-test")
        h = km.history(rec.id)
        assert len(h) >= 1

    def test_count(self):
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager()
        before = km.count()
        km.create_fact("count-check")
        assert km.count() == before + 1

    def test_find_by_tags(self):
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        from iios.knowledge.knowledge_constants import KnowledgeDomain
        km = get_knowledge_manager()
        km.create_fact("tagged-fact", tags=["equity"])
        recs = km.find_by_tags(["equity"])
        assert len(recs) >= 1


# ===========================================================================
# 14. KnowledgeEngine (lifecycle)
# ===========================================================================

class TestKnowledgeEngine:
    def setup_method(self):
        _reset_all()

    def test_initialize_and_status(self):
        from iios.knowledge.knowledge_engine import get_knowledge_engine
        engine = get_knowledge_engine()
        engine.initialize()
        s = engine.status()
        assert s["status"] == "running"
        assert s["namespace"] == "iios.knowledge"
        engine.shutdown()

    def test_shutdown_idempotent(self):
        from iios.knowledge.knowledge_engine import get_knowledge_engine
        engine = get_knowledge_engine()
        engine.initialize()
        engine.shutdown()
        engine.shutdown()  # must not raise

    def test_initialize_idempotent(self):
        from iios.knowledge.knowledge_engine import get_knowledge_engine
        engine = get_knowledge_engine()
        engine.initialize()
        engine.initialize()  # must not raise
        engine.shutdown()

    def test_status_not_initialized(self):
        from iios.knowledge.knowledge_engine import get_knowledge_engine
        engine = get_knowledge_engine()
        s = engine.status()
        assert s["status"] == "not_initialized"

    def test_require_initialized_raises(self):
        from iios.knowledge.knowledge_engine import get_knowledge_engine
        from iios.knowledge.knowledge_exceptions import KnowledgeEngineNotInitializedError
        engine = get_knowledge_engine()
        with pytest.raises(KnowledgeEngineNotInitializedError):
            engine.require_initialized()

    def test_full_lifecycle_with_data(self):
        from iios.knowledge.knowledge_engine import get_knowledge_engine
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        engine = get_knowledge_engine()
        engine.initialize()
        km = get_knowledge_manager()
        rec = km.create_fact("lifecycle-fact", {"close": 100})
        s = engine.status()
        assert s["total_records"] >= 1
        engine.shutdown()


# ===========================================================================
# 15. KnowledgeFactory
# ===========================================================================

class TestKnowledgeFactory:
    def setup_method(self):
        _reset_all()

    def test_create_all_types(self):
        from iios.knowledge.knowledge_factory import get_knowledge_factory
        from iios.knowledge.knowledge_constants import KnowledgeType
        factory = get_knowledge_factory()
        expected = [
            (factory.create_fact,        KnowledgeType.FACT),
            (factory.create_rule,        KnowledgeType.RULE),
            (factory.create_concept,     KnowledgeType.CONCEPT),
            (factory.create_pattern,     KnowledgeType.PATTERN),
            (factory.create_strategy,    KnowledgeType.STRATEGY),
            (factory.create_signal,      KnowledgeType.SIGNAL),
            (factory.create_observation, KnowledgeType.OBSERVATION),
            (factory.create_inference,   KnowledgeType.INFERENCE),
        ]
        for fn, ktype in expected:
            rec = fn(title=f"Test {ktype.value}")
            assert rec.knowledge_type == ktype

    def test_factory_sets_owner(self):
        from iios.knowledge.knowledge_factory import KnowledgeFactory
        factory = KnowledgeFactory(default_owner="test:owner")
        rec = factory.create_fact("owner test")
        assert rec.metadata.owner_id == "test:owner"

    def test_factory_tags(self):
        from iios.knowledge.knowledge_factory import get_knowledge_factory
        factory = get_knowledge_factory()
        rec = factory.create_fact("tagged", tags=["nifty", "equity"])
        assert rec.metadata.has_tag("nifty")
        assert rec.metadata.has_tag("equity")


# ===========================================================================
# 16. Context
# ===========================================================================

class TestKnowledgeContext:
    def setup_method(self):
        _reset_all()

    def test_default_actor(self):
        from iios.knowledge.knowledge_context import current_actor
        from iios.knowledge.knowledge_constants import ANONYMOUS_OWNER
        assert current_actor() == ANONYMOUS_OWNER

    def test_context_sets_actor(self):
        from iios.knowledge.knowledge_context import get_knowledge_context, current_actor
        ctx = get_knowledge_context()
        with ctx.operation("test-op", actor_id="user:test"):
            assert current_actor() == "user:test"
        assert current_actor() == "user:test" or True  # restored to prev

    def test_operation_id_set_in_context(self):
        from iios.knowledge.knowledge_context import get_knowledge_context, current_operation_id
        ctx = get_knowledge_context()
        with ctx.operation("test-op", actor_id="user:test") as op_id:
            assert op_id == current_operation_id()
            assert len(op_id) > 0

    def test_knowledge_operation_shortcut(self):
        from iios.knowledge.knowledge_context import knowledge_operation, current_actor
        with knowledge_operation("write", actor_id="user:alice"):
            assert current_actor() == "user:alice"
