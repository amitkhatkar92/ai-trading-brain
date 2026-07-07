"""
tests/unit/knowledge/test_version_engine.py
============================================
Comprehensive test suite for the Knowledge Versioning & Evolution Engine.

Test classes:
  01 TestVersionConstants         — enum values and module constants
  02 TestVersionExceptions        — exception hierarchy and attributes
  03 TestKnowledgeVersion         — model dataclass, properties, serde
  04 TestVersionHistory           — filtering, queries, major_versions
  05 TestVersionBranch            — lifecycle, add_version, mark_merged
  06 TestVersionDiff              — FieldChange, RecordDiff helpers
  07 TestAuditEntry               — serde roundtrip
  08 TestProvenanceRecord         — serde roundtrip, has_source
  09 TestLineageGraph             — node/edge queries
  10 TestVersionManager           — CRUD, lifecycle transitions, rollback
  11 TestBranchManager            — create, register, merge strategies
  12 TestDiffEngine               — delta, diff, conflict detection
  13 TestAuditLog                 — log, get_trail, statistics
  14 TestProvenanceTracker        — record, get, sources
  15 TestLineageManager           — edge management, traversal, cycle guard
  16 TestDependencyTracker        — add/remove/query dependencies
  17 TestVersionContext           — thread-local context manager
  18 TestVersionFactory           — all factory convenience methods
  19 TestVersionEngine            — integration: full lifecycle
  20 TestVersionRegistry          — register, get, status
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from iios.knowledge.knowledge_constants import VersionBump
from iios.knowledge.models.knowledge_record import KnowledgeRecord
from iios.knowledge.versioning.version_constants import (
    BranchStatus,
    ChangeType,
    LineageRelationType,
    MergeStrategy,
    ProvenanceType,
    VersionEventType,
    DEFAULT_BRANCH,
    SYSTEM_VERSIONING_ACTOR,
    VERSIONING_NAMESPACE,
    MAX_LINEAGE_DEPTH,
    DIFF_SKIP_FIELDS,
)
from iios.knowledge.versioning.version_exceptions import (
    AuditError,
    BranchAlreadyExistsError,
    BranchConflictError,
    BranchMergeError,
    BranchNotFoundError,
    DiffError,
    LineageCycleError,
    LineageError,
    ProvenanceError,
    VersionAlreadyExistsError,
    VersionEngineError,
    VersionError,
    VersionNotFoundError,
    VersionRollbackError,
    VersionValidationError,
)
from iios.knowledge.versioning.models.knowledge_version import (
    KnowledgeVersion, VersionStatus,
)
from iios.knowledge.versioning.models.version_history import VersionHistory
from iios.knowledge.versioning.models.version_branch import (
    ConflictInfo, MergeResult, VersionBranch,
)
from iios.knowledge.versioning.models.version_diff import FieldChange, RecordDiff
from iios.knowledge.versioning.models.version_audit import AuditEntry
from iios.knowledge.versioning.models.provenance_record import ProvenanceRecord
from iios.knowledge.versioning.models.lineage_graph import (
    LineageEdge, LineageGraph, LineageNode,
)
from iios.knowledge.versioning.version_manager import (
    VersionManager, get_version_manager, reset_version_manager,
)
from iios.knowledge.versioning.branch_manager import (
    BranchManager, get_branch_manager, reset_branch_manager,
)
from iios.knowledge.versioning.diff_engine import (
    DiffEngine, get_diff_engine, reset_diff_engine,
)
from iios.knowledge.versioning.audit_log import (
    AuditLog, get_audit_log, reset_audit_log,
)
from iios.knowledge.versioning.provenance_tracker import (
    ProvenanceTracker, get_provenance_tracker, reset_provenance_tracker,
)
from iios.knowledge.versioning.lineage_manager import (
    DependencyTracker, LineageManager,
    get_dependency_tracker, get_lineage_manager,
    reset_dependency_tracker, reset_lineage_manager,
)
from iios.knowledge.versioning.version_context import (
    VersionContext, current_version_actor, current_version_operation_id,
    get_version_context, reset_version_context, version_operation,
)
from iios.knowledge.versioning.version_factory import (
    VersionFactory, get_version_factory, reset_version_factory,
)
from iios.knowledge.versioning.version_engine import (
    VersionEngine, get_version_engine, reset_version_engine,
)
from iios.knowledge.versioning.version_registry import (
    VersionRegistry, get_version_registry, reset_version_registry,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_record(title: str = "Test") -> KnowledgeRecord:
    return KnowledgeRecord(title=title)


def _reset_all() -> None:
    reset_version_manager()
    reset_branch_manager()
    reset_diff_engine()
    reset_audit_log()
    reset_provenance_tracker()
    reset_lineage_manager()
    reset_dependency_tracker()
    reset_version_context()
    reset_version_factory()
    reset_version_engine()
    reset_version_registry()


# ══════════════════════════════════════════════════════════════════════════════
# 01  TestVersionConstants
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionConstants:
    def test_default_branch(self):
        assert DEFAULT_BRANCH == "main"

    def test_system_actor(self):
        assert SYSTEM_VERSIONING_ACTOR == "iios:system"

    def test_versioning_namespace(self):
        assert VERSIONING_NAMESPACE == "iios.versioning"

    def test_branch_status_enum_values(self):
        assert BranchStatus.OPEN.value == "open"
        assert BranchStatus.MERGED.value == "merged"
        assert BranchStatus.CLOSED.value == "closed"

    def test_merge_strategy_enum(self):
        strats = {s.value for s in MergeStrategy}
        assert {"ours", "theirs", "latest", "manual"}.issubset(strats)

    def test_change_type_enum(self):
        assert ChangeType.ADDED.value == "added"
        assert ChangeType.MODIFIED.value == "modified"
        assert ChangeType.REMOVED.value == "removed"

    def test_provenance_type_enum(self):
        assert ProvenanceType.CREATED.value == "created"
        assert ProvenanceType.DERIVED_FROM.value == "derived_from"

    def test_lineage_relation_enum(self):
        assert LineageRelationType.DERIVED_FROM.value == "derived_from"
        assert LineageRelationType.DEPENDS_ON.value == "depends_on"

    def test_version_event_type_enum(self):
        assert VersionEventType.VERSION_CREATED.value == "version.created"
        assert VersionEventType.BRANCH_MERGED.value == "branch.merged"

    def test_diff_skip_fields_frozen(self):
        assert isinstance(DIFF_SKIP_FIELDS, frozenset)
        assert "updated_at" in DIFF_SKIP_FIELDS

    def test_max_lineage_depth(self):
        assert MAX_LINEAGE_DEPTH >= 10


# ══════════════════════════════════════════════════════════════════════════════
# 02  TestVersionExceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionExceptions:
    def test_version_error_is_base(self):
        e = VersionError("test")
        from iios.knowledge.knowledge_exceptions import KnowledgeVersionError
        assert isinstance(e, KnowledgeVersionError)

    def test_version_not_found_error(self):
        e = VersionNotFoundError("v1 missing")
        assert "v1 missing" in str(e)

    def test_branch_conflict_error_fields(self):
        e = BranchConflictError("conflict", conflict_fields=["title", "content"])
        assert e.conflict_fields == ["title", "content"]

    def test_version_validation_error_violations(self):
        e = VersionValidationError("bad", violations=["must be > 0"])
        assert "must be > 0" in e.violations

    def test_lineage_cycle_error_inherits(self):
        e = LineageCycleError("cycle")
        assert isinstance(e, LineageError)

    def test_exception_codes(self):
        assert VersionNotFoundError("x").code == "VE-001"
        assert BranchNotFoundError("x").code == "VE-101"
        assert DiffError("x").code == "VE-200"

    def test_audit_error(self):
        e = AuditError("bad audit")
        assert isinstance(e, VersionError)


# ══════════════════════════════════════════════════════════════════════════════
# 03  TestKnowledgeVersion
# ══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeVersion:
    def test_create_default(self):
        kv = KnowledgeVersion(knowledge_id="kid-1", version_string="1.0.0")
        assert kv.version_string == "1.0.0"
        assert kv.status == VersionStatus.CURRENT
        assert kv.branch_name == DEFAULT_BRANCH

    def test_version_properties(self):
        kv = KnowledgeVersion(version_string="3.7.11")
        assert kv.major == 3
        assert kv.minor == 7
        assert kv.patch == 11

    def test_is_current(self):
        kv = KnowledgeVersion(status=VersionStatus.CURRENT)
        assert kv.is_current
        assert not kv.is_draft

    def test_is_draft(self):
        kv = KnowledgeVersion(status=VersionStatus.DRAFT)
        assert kv.is_draft

    def test_is_released(self):
        kv = KnowledgeVersion(status=VersionStatus.RELEASED)
        assert kv.is_released

    def test_to_dict_roundtrip(self):
        kv = KnowledgeVersion(
            knowledge_id   = "test-id",
            version_string = "2.1.3",
            version_seq    = 5,
            author         = "user:alice",
            change_summary = "Updated",
        )
        d  = kv.to_dict()
        kv2 = KnowledgeVersion.from_dict(d)
        assert kv2.knowledge_id   == "test-id"
        assert kv2.version_string == "2.1.3"
        assert kv2.version_seq    == 5
        assert kv2.author         == "user:alice"

    def test_from_dict_with_missing_fields(self):
        kv = KnowledgeVersion.from_dict({"knowledge_id": "x"})
        assert kv.version_string == "1.0.0"

    def test_tags_and_attributes(self):
        kv = KnowledgeVersion(
            tags       = ["stable", "finance"],
            attributes = {"source": "ml"},
        )
        assert "stable" in kv.tags
        assert kv.attributes["source"] == "ml"

    def test_merged_from_ids(self):
        kv = KnowledgeVersion(merged_from_ids=["v1", "v2"])
        assert len(kv.merged_from_ids) == 2


# ══════════════════════════════════════════════════════════════════════════════
# 04  TestVersionHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionHistory:
    def _sample_history(self) -> VersionHistory:
        versions = [
            KnowledgeVersion(
                knowledge_id   = "k1",
                version_string = f"1.{i}.0",
                version_seq    = i + 1,
                status         = (VersionStatus.CURRENT if i == 2
                                  else VersionStatus.ARCHIVED),
            )
            for i in range(3)
        ]
        return VersionHistory(knowledge_id="k1", versions=versions)

    def test_count(self):
        h = self._sample_history()
        assert h.count == 3

    def test_latest(self):
        h = self._sample_history()
        assert h.latest().version_string == "1.2.0"

    def test_earliest(self):
        h = self._sample_history()
        assert h.earliest().version_string == "1.0.0"

    def test_get_by_id(self):
        h = self._sample_history()
        vid = h.versions[1].version_id
        assert h.get(vid).version_string == "1.1.0"

    def test_get_missing_returns_none(self):
        h = self._sample_history()
        assert h.get("nonexistent") is None

    def test_filter_by_status(self):
        h = self._sample_history()
        currents = h.filter(status=VersionStatus.CURRENT)
        assert len(currents) == 1

    def test_since(self):
        h = self._sample_history()
        vid = h.versions[0].version_id
        after = h.since(vid)
        assert len(after) == 2

    def test_major_versions(self):
        versions = [
            KnowledgeVersion(knowledge_id="k", version_string="1.0.0", version_seq=1),
            KnowledgeVersion(knowledge_id="k", version_string="1.1.0", version_seq=2),
            KnowledgeVersion(knowledge_id="k", version_string="2.0.0", version_seq=3),
        ]
        h = VersionHistory(knowledge_id="k", versions=versions)
        majors = h.major_versions()
        assert len(majors) == 2
        assert majors[0].major == 1
        assert majors[1].major == 2

    def test_version_strings(self):
        h = self._sample_history()
        assert "1.0.0" in h.version_strings()

    def test_is_empty_on_empty_history(self):
        h = VersionHistory(knowledge_id="x")
        assert h.is_empty

    def test_to_dict(self):
        h = self._sample_history()
        d = h.to_dict()
        assert d["count"] == 3
        assert len(d["versions"]) == 3


# ══════════════════════════════════════════════════════════════════════════════
# 05  TestVersionBranch
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionBranch:
    def test_create_default(self):
        b = VersionBranch(knowledge_id="k", name="main")
        assert b.status == BranchStatus.OPEN
        assert b.is_main

    def test_add_version(self):
        b = VersionBranch(knowledge_id="k", name="feature/x")
        b.add_version("v1")
        b.add_version("v2")
        assert b.commit_count == 2
        assert b.head_version_id == "v2"

    def test_mark_merged(self):
        b = VersionBranch(knowledge_id="k", name="feature/x")
        b.mark_merged("main", "user:alice")
        assert b.status == BranchStatus.MERGED
        assert b.merged_into == "main"
        assert b.merged_by == "user:alice"

    def test_mark_closed(self):
        b = VersionBranch(knowledge_id="k", name="temp")
        b.mark_closed()
        assert b.status == BranchStatus.CLOSED

    def test_to_dict_roundtrip(self):
        b = VersionBranch(knowledge_id="k", name="experimental")
        b.add_version("vid1")
        d  = b.to_dict()
        b2 = VersionBranch.from_dict(d)
        assert b2.name == "experimental"
        assert b2.version_ids == ["vid1"]

    def test_head_version_id_none_when_empty(self):
        b = VersionBranch(knowledge_id="k", name="empty")
        assert b.head_version_id is None


# ══════════════════════════════════════════════════════════════════════════════
# 06  TestVersionDiff
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionDiff:
    def test_field_change_properties(self):
        fc = FieldChange("title", ChangeType.MODIFIED, "old", "new")
        assert fc.is_modification
        assert not fc.is_addition
        assert not fc.is_removal

    def test_field_change_added(self):
        fc = FieldChange("tags", ChangeType.ADDED, None, ["a"])
        assert fc.is_addition

    def test_record_diff_changed_fields(self):
        rd = RecordDiff(
            knowledge_id   = "k",
            field_changes  = [
                FieldChange("title",   ChangeType.MODIFIED, "A", "B"),
                FieldChange("content", ChangeType.MODIFIED, 1,   2),
            ],
        )
        assert "title" in rd.changed_fields
        assert rd.change_count == 2

    def test_record_diff_get_change(self):
        fc = FieldChange("title", ChangeType.MODIFIED, "A", "B")
        rd = RecordDiff(knowledge_id="k", field_changes=[fc])
        found = rd.get_change("title")
        assert found is fc

    def test_record_diff_added_modified_removed(self):
        rd = RecordDiff(
            knowledge_id = "k",
            field_changes = [
                FieldChange("a", ChangeType.ADDED,    None, 1),
                FieldChange("b", ChangeType.MODIFIED, 1,    2),
                FieldChange("c", ChangeType.REMOVED,  3,    None),
            ],
        )
        assert rd.added_fields()    == ["a"]
        assert rd.modified_fields() == ["b"]
        assert rd.removed_fields()  == ["c"]

    def test_record_diff_is_empty(self):
        rd = RecordDiff(knowledge_id="k")
        assert rd.is_empty

    def test_record_diff_to_dict(self):
        fc = FieldChange("x", ChangeType.ADDED, None, 5)
        rd = RecordDiff(knowledge_id="k", field_changes=[fc])
        d  = rd.to_dict()
        rd2 = RecordDiff.from_dict(d)
        assert rd2.knowledge_id == "k"
        assert rd2.field_changes[0].field_name == "x"


# ══════════════════════════════════════════════════════════════════════════════
# 07  TestAuditEntry
# ══════════════════════════════════════════════════════════════════════════════

class TestAuditEntry:
    def test_create_default(self):
        ae = AuditEntry(
            knowledge_id = "k",
            event_type   = VersionEventType.VERSION_CREATED,
            actor        = "user:test",
        )
        assert ae.actor == "user:test"
        assert ae.event_type == VersionEventType.VERSION_CREATED

    def test_to_dict_roundtrip(self):
        ae = AuditEntry(
            knowledge_id = "k",
            event_type   = VersionEventType.BRANCH_CREATED,
            actor        = "user:bob",
            reason       = "testing",
            details      = {"branch": "feature"},
        )
        d   = ae.to_dict()
        ae2 = AuditEntry.from_dict(d)
        assert ae2.actor  == "user:bob"
        assert ae2.reason == "testing"
        assert ae2.details["branch"] == "feature"

    def test_from_dict_defaults(self):
        ae = AuditEntry.from_dict({"knowledge_id": "x"})
        assert ae.knowledge_id == "x"
        assert ae.actor == SYSTEM_VERSIONING_ACTOR


# ══════════════════════════════════════════════════════════════════════════════
# 08  TestProvenanceRecord
# ══════════════════════════════════════════════════════════════════════════════

class TestProvenanceRecord:
    def test_create(self):
        pr = ProvenanceRecord(
            knowledge_id    = "k",
            provenance_type = ProvenanceType.DERIVED_FROM,
            source_id       = "src-1",
        )
        assert pr.has_source
        assert not pr.is_creation

    def test_created_type(self):
        pr = ProvenanceRecord(provenance_type=ProvenanceType.CREATED)
        assert pr.is_creation

    def test_to_dict_roundtrip(self):
        pr = ProvenanceRecord(
            knowledge_id    = "k",
            provenance_type = ProvenanceType.IMPORTED,
            transformation  = "csv_import",
            actor           = "user:importer",
        )
        d   = pr.to_dict()
        pr2 = ProvenanceRecord.from_dict(d)
        assert pr2.transformation == "csv_import"
        assert pr2.provenance_type == ProvenanceType.IMPORTED

    def test_no_source(self):
        pr = ProvenanceRecord(knowledge_id="k")
        assert not pr.has_source


# ══════════════════════════════════════════════════════════════════════════════
# 09  TestLineageGraph
# ══════════════════════════════════════════════════════════════════════════════

class TestLineageGraph:
    def _sample_graph(self) -> LineageGraph:
        nodes = [
            LineageNode("n1", label="Root", depth=0),
            LineageNode("n2", label="Child A", depth=1),
            LineageNode("n3", label="Child B", depth=1),
        ]
        edges = [
            LineageEdge("n1", "n2", LineageRelationType.DERIVED_FROM),
            LineageEdge("n1", "n3", LineageRelationType.DERIVED_FROM),
        ]
        return LineageGraph(root_id="n1", nodes=nodes, edges=edges, depth=1)

    def test_node_count(self):
        g = self._sample_graph()
        assert g.node_count == 3

    def test_edge_count(self):
        g = self._sample_graph()
        assert g.edge_count == 2

    def test_get_node(self):
        g = self._sample_graph()
        n = g.get_node("n2")
        assert n.label == "Child A"

    def test_ancestors_of(self):
        g = self._sample_graph()
        parents = g.ancestors_of("n2")
        assert "n1" in parents

    def test_descendants_of(self):
        g = self._sample_graph()
        children = g.descendants_of("n1")
        assert "n2" in children
        assert "n3" in children

    def test_all_node_ids(self):
        g = self._sample_graph()
        ids = g.all_node_ids()
        assert set(ids) == {"n1", "n2", "n3"}

    def test_to_dict(self):
        g = self._sample_graph()
        d = g.to_dict()
        assert d["root_id"] == "n1"
        assert d["node_count"] == 3


# ══════════════════════════════════════════════════════════════════════════════
# 10  TestVersionManager
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionManager:
    def setup_method(self):
        _reset_all()
        self.vm = VersionManager()

    def test_create_version_bumps_record(self):
        record = _make_record("Facts")
        v = self.vm.create_version(record, VersionBump.MINOR)
        assert v.version_string == "1.1.0"
        assert record.version == "1.1.0"
        assert record.version_sequence == 2

    def test_create_major_bump(self):
        record = _make_record()
        v = self.vm.create_version(record, VersionBump.MAJOR)
        assert v.version_string == "2.0.0"

    def test_create_patch_bump(self):
        record = _make_record()
        v = self.vm.create_version(record, VersionBump.PATCH)
        assert v.version_string == "1.0.1"

    def test_get_version(self):
        record = _make_record()
        v = self.vm.create_version(record)
        fetched = self.vm.get(v.version_id)
        assert fetched.version_id == v.version_id

    def test_get_nonexistent_raises(self):
        with pytest.raises(VersionNotFoundError):
            self.vm.get("does-not-exist")

    def test_get_latest(self):
        record = _make_record()
        v1 = self.vm.create_version(record, VersionBump.MINOR)
        v2 = self.vm.create_version(record, VersionBump.MINOR)
        latest = self.vm.get_latest(record.id)
        assert latest.version_id == v2.version_id

    def test_list_versions(self):
        record = _make_record()
        self.vm.create_version(record)
        self.vm.create_version(record)
        versions = self.vm.list_versions(record.id)
        assert len(versions) == 2

    def test_list_versions_by_branch(self):
        record = _make_record()
        v1 = self.vm.create_version(record, branch="main")
        v2 = self.vm.create_version(record, branch="feature")
        main_versions = self.vm.list_versions(record.id, branch="main")
        # v1 may be archived by v2, both should appear
        main_ids = [v.version_id for v in main_versions]
        assert v1.version_id in main_ids

    def test_release_version(self):
        record = _make_record()
        v = self.vm.create_version(record)
        released = self.vm.release(v.version_id)
        assert released.status == VersionStatus.RELEASED

    def test_release_archived_raises(self):
        record = _make_record()
        v = self.vm.create_version(record)
        self.vm.archive(v.version_id)
        with pytest.raises(VersionValidationError):
            self.vm.release(v.version_id)

    def test_archive_version(self):
        record = _make_record()
        v = self.vm.create_version(record)
        archived = self.vm.archive(v.version_id)
        assert archived.status == VersionStatus.ARCHIVED

    def test_soft_delete(self):
        record = _make_record()
        v = self.vm.create_version(record)
        deleted = self.vm.soft_delete(v.version_id)
        assert deleted.status == VersionStatus.DELETED
        # Soft deleted excluded from list by default
        versions = self.vm.list_versions(record.id)
        assert v.version_id not in [vv.version_id for vv in versions]

    def test_promote_draft(self):
        record = _make_record()
        v = self.vm.create_version(record, is_draft=True)
        assert v.status == VersionStatus.DRAFT
        promoted = self.vm.promote_draft(v.version_id)
        assert promoted.status == VersionStatus.CURRENT

    def test_promote_non_draft_raises(self):
        record = _make_record()
        v = self.vm.create_version(record)
        with pytest.raises(VersionValidationError):
            self.vm.promote_draft(v.version_id)

    def test_rollback(self):
        record = _make_record("Original")
        v1 = self.vm.create_version(record, author="user:alice")
        record.title = "Modified"
        v2 = self.vm.create_version(record, author="user:alice")
        # Rollback to v1
        record, rollback_v = self.vm.rollback(record, v1.version_id, "user:bob")
        assert record.title == "Original"
        assert rollback_v.status == VersionStatus.ROLLBACK

    def test_rollback_nonexistent_raises(self):
        record = _make_record()
        with pytest.raises(VersionNotFoundError):
            self.vm.rollback(record, "bad-id")

    def test_version_count(self):
        record = _make_record()
        for _ in range(4):
            self.vm.create_version(record)
        assert self.vm.version_count(record.id) == 4

    def test_statistics(self):
        record = _make_record()
        self.vm.create_version(record)
        stats = self.vm.statistics()
        assert stats["total_versions"] == 1
        assert stats["unique_items"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# 11  TestBranchManager
# ══════════════════════════════════════════════════════════════════════════════

class TestBranchManager:
    def setup_method(self):
        _reset_all()
        self.vm = VersionManager()
        self.bm = BranchManager()
        self.de = DiffEngine()

    def test_create_branch(self):
        b = self.bm.create_branch("k1", "feature/x")
        assert b.name == "feature/x"
        assert b.status == BranchStatus.OPEN

    def test_duplicate_branch_raises(self):
        self.bm.create_branch("k1", "feature/y")
        with pytest.raises(BranchAlreadyExistsError):
            self.bm.create_branch("k1", "feature/y")

    def test_get_branch(self):
        self.bm.create_branch("k1", "feat")
        b = self.bm.get("k1", "feat")
        assert b.name == "feat"

    def test_get_nonexistent_raises(self):
        with pytest.raises(BranchNotFoundError):
            self.bm.get("k1", "no-branch")

    def test_list_branches(self):
        self.bm.create_branch("k2", "main")
        self.bm.create_branch("k2", "dev")
        branches = self.bm.list_branches("k2")
        assert len(branches) == 2

    def test_ensure_main_branch_idempotent(self):
        b1 = self.bm.ensure_main_branch("k3")
        b2 = self.bm.ensure_main_branch("k3")
        assert b1.branch_id == b2.branch_id

    def test_register_version(self):
        self.bm.ensure_main_branch("k4")
        self.bm.register_version("k4", DEFAULT_BRANCH, "vid1")
        b = self.bm.get("k4", DEFAULT_BRANCH)
        assert "vid1" in b.version_ids

    def test_merge_theirs_strategy(self):
        record = _make_record("Base")
        # Set up ancestor
        anc = self.vm.create_version(record, VersionBump.MINOR, branch="main")
        # Main branch
        self.bm.ensure_main_branch(record.id, anc.version_id)
        self.bm.register_version(record.id, "main", anc.version_id)
        # Create feature branch
        self.bm.create_branch(record.id, "feature/a",
                              source_version_id=anc.version_id)
        # Add version on feature branch
        record.title = "Feature Title"
        feat_v = self.vm.create_version(record, VersionBump.MINOR, branch="feature/a")
        self.bm.register_version(record.id, "feature/a", feat_v.version_id)
        # Merge
        result = self.bm.merge(
            knowledge_id   = record.id,
            source_branch  = "feature/a",
            target_branch  = "main",
            strategy       = MergeStrategy.THEIRS,
            version_manager = self.vm,
            diff_engine    = self.de,
        )
        assert result.success
        assert result.new_version_id is not None
        merged_v = self.vm.get(result.new_version_id)
        assert merged_v.payload.get("title") == "Feature Title"

    def test_merge_ours_strategy(self):
        record = _make_record("Base")
        anc = self.vm.create_version(record, VersionBump.MINOR, branch="main")
        self.bm.ensure_main_branch(record.id, anc.version_id)
        self.bm.register_version(record.id, "main", anc.version_id)
        self.bm.create_branch(record.id, "feature/b",
                              source_version_id=anc.version_id)
        record.title = "Feature Title"
        feat_v = self.vm.create_version(record, VersionBump.MINOR, branch="feature/b")
        self.bm.register_version(record.id, "feature/b", feat_v.version_id)
        result = self.bm.merge(
            knowledge_id   = record.id,
            source_branch  = "feature/b",
            target_branch  = "main",
            strategy       = MergeStrategy.OURS,
            version_manager = self.vm,
            diff_engine    = self.de,
        )
        assert result.success
        # OURS = keep main (which has "Base")
        merged_v = self.vm.get(result.new_version_id)
        assert merged_v.payload.get("title") == "Base"

    def test_merge_marks_source_branch_merged(self):
        record = _make_record("X")
        anc = self.vm.create_version(record, VersionBump.MINOR, branch="main")
        self.bm.ensure_main_branch(record.id, anc.version_id)
        self.bm.register_version(record.id, "main", anc.version_id)
        self.bm.create_branch(record.id, "feature/c",
                              source_version_id=anc.version_id)
        record.title = "Modified"
        fv = self.vm.create_version(record, branch="feature/c")
        self.bm.register_version(record.id, "feature/c", fv.version_id)
        self.bm.merge(
            knowledge_id   = record.id,
            source_branch  = "feature/c",
            target_branch  = "main",
            strategy       = MergeStrategy.THEIRS,
            version_manager = self.vm,
            diff_engine    = self.de,
        )
        src_branch = self.bm.get(record.id, "feature/c")
        assert src_branch.status == BranchStatus.MERGED

    def test_merge_manual_conflict_raises(self):
        record = _make_record("Orig")
        anc = self.vm.create_version(record, VersionBump.MINOR, branch="main")
        self.bm.ensure_main_branch(record.id, anc.version_id)
        self.bm.register_version(record.id, "main", anc.version_id)
        self.bm.create_branch(record.id, "feature/d",
                              source_version_id=anc.version_id)
        # Modify on feature branch
        record.title = "Feature Title"
        feat_v = self.vm.create_version(record, branch="feature/d")
        self.bm.register_version(record.id, "feature/d", feat_v.version_id)
        # Also modify on main
        record.title = "Main Title"
        main_v = self.vm.create_version(record, branch="main")
        self.bm.register_version(record.id, "main", main_v.version_id)
        # Manual merge should detect title conflict and raise
        with pytest.raises(BranchConflictError):
            self.bm.merge(
                knowledge_id   = record.id,
                source_branch  = "feature/d",
                target_branch  = "main",
                strategy       = MergeStrategy.MANUAL,
                version_manager = self.vm,
                diff_engine    = self.de,
            )


# ══════════════════════════════════════════════════════════════════════════════
# 12  TestDiffEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestDiffEngine:
    def setup_method(self):
        _reset_all()
        self.de = DiffEngine()

    def test_no_changes_on_identical(self):
        payload = {"title": "A", "content": "hello"}
        changes = self.de.compute_delta(payload, payload)
        assert changes == []

    def test_modified_field(self):
        before = {"title": "Old", "x": 1}
        after  = {"title": "New", "x": 1}
        changes = self.de.compute_delta(before, after)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.MODIFIED
        assert changes[0].field_name  == "title"

    def test_added_field(self):
        before = {"x": 1}
        after  = {"x": 1, "y": 2}
        changes = self.de.compute_delta(before, after)
        assert any(c.change_type == ChangeType.ADDED and c.field_name == "y"
                   for c in changes)

    def test_removed_field(self):
        before = {"x": 1, "z": 3}
        after  = {"x": 1}
        changes = self.de.compute_delta(before, after)
        assert any(c.change_type == ChangeType.REMOVED and c.field_name == "z"
                   for c in changes)

    def test_skip_fields_excluded(self):
        before = {"title": "A", "updated_at": 1000.0}
        after  = {"title": "A", "updated_at": 2000.0}
        changes = self.de.compute_delta(before, after)
        assert not any(c.field_name == "updated_at" for c in changes)

    def test_compute_diff_between_versions(self):
        vm = VersionManager()
        r  = _make_record("Initial")
        v1 = vm.create_version(r, VersionBump.SNAPSHOT)
        r.title = "Updated"
        v2 = vm.create_version(r, VersionBump.MINOR)
        diff = self.de.compute_diff(r.id, v1, v2)
        assert diff.knowledge_id == r.id
        assert diff.version_id_before == v1.version_id
        assert diff.version_id_after  == v2.version_id
        assert "title" in diff.changed_fields

    def test_detect_conflict_fields(self):
        src_diff = RecordDiff(knowledge_id="k", field_changes=[
            FieldChange("title", ChangeType.MODIFIED, "A", "B"),
            FieldChange("value", ChangeType.MODIFIED, 1,   2),
        ])
        tgt_diff = RecordDiff(knowledge_id="k", field_changes=[
            FieldChange("title",  ChangeType.MODIFIED, "A", "C"),
            FieldChange("status", ChangeType.MODIFIED, "x", "y"),
        ])
        conflicts = self.de.detect_conflict_fields(src_diff, tgt_diff)
        assert "title" in conflicts

    def test_summary_generated(self):
        before = {"a": 1}
        after  = {"a": 2}
        changes = self.de.compute_delta(before, after)
        summary = DiffEngine._summarize(changes)
        assert "a" in summary

    def test_empty_diff_summary(self):
        summary = DiffEngine._summarize([])
        assert summary == "No changes."


# ══════════════════════════════════════════════════════════════════════════════
# 13  TestAuditLog
# ══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:
    def setup_method(self):
        _reset_all()
        self.al = AuditLog()

    def test_log_entry(self):
        entry = self.al.log("k1", VersionEventType.VERSION_CREATED,
                             actor="user:a", reason="created")
        assert entry.knowledge_id == "k1"
        assert entry.actor == "user:a"

    def test_get_trail(self):
        self.al.log("k2", VersionEventType.VERSION_CREATED)
        self.al.log("k2", VersionEventType.VERSION_RELEASED)
        trail = self.al.get_trail("k2")
        assert len(trail) == 2

    def test_get_trail_filter_event(self):
        self.al.log("k3", VersionEventType.VERSION_CREATED)
        self.al.log("k3", VersionEventType.VERSION_ARCHIVED)
        trail = self.al.get_trail("k3",
                                   event_type=VersionEventType.VERSION_CREATED)
        assert len(trail) == 1

    def test_get_trail_newest_first(self):
        self.al.log("k4", VersionEventType.VERSION_CREATED)
        self.al.log("k4", VersionEventType.BRANCH_CREATED)
        trail = self.al.get_trail("k4")
        assert trail[0].event_type == VersionEventType.BRANCH_CREATED

    def test_get_entry(self):
        entry = self.al.log("k5", VersionEventType.VERSION_CREATED)
        fetched = self.al.get_entry(entry.audit_id)
        assert fetched.audit_id == entry.audit_id

    def test_get_missing_entry_raises(self):
        with pytest.raises(AuditError):
            self.al.get_entry("no-such-id")

    def test_entry_count(self):
        self.al.log("k6", VersionEventType.VERSION_CREATED)
        self.al.log("k6", VersionEventType.VERSION_CREATED)
        assert self.al.entry_count("k6") == 2

    def test_statistics(self):
        self.al.log("k7", VersionEventType.VERSION_CREATED)
        stats = self.al.statistics()
        assert stats["total_entries"] >= 1
        assert "version.created" in stats["by_event_type"]


# ══════════════════════════════════════════════════════════════════════════════
# 14  TestProvenanceTracker
# ══════════════════════════════════════════════════════════════════════════════

class TestProvenanceTracker:
    def setup_method(self):
        _reset_all()
        self.pt = ProvenanceTracker()

    def test_record_creation(self):
        pr = self.pt.record_creation("k1", actor="user:a")
        assert pr.provenance_type == ProvenanceType.CREATED
        assert pr.knowledge_id == "k1"

    def test_record_derivation(self):
        pr = self.pt.record_derivation("k2", "k1", "enrichment")
        assert pr.provenance_type == ProvenanceType.DERIVED_FROM
        assert pr.source_id == "k1"
        assert pr.transformation == "enrichment"

    def test_record_merge(self):
        records = self.pt.record_merge("k3", ["src1", "src2"])
        assert len(records) == 2
        assert all(r.provenance_type == ProvenanceType.MERGED_FROM
                   for r in records)

    def test_get_provenance(self):
        self.pt.record_creation("k4")
        self.pt.record_derivation("k4", "k0", "transform")
        prv = self.pt.get_provenance("k4")
        assert len(prv) == 2

    def test_get_origin(self):
        self.pt.record_derivation("k5", "k0", "transform")
        self.pt.record_creation("k5")
        origin = self.pt.get_origin("k5")
        assert origin is not None
        assert origin.provenance_type == ProvenanceType.CREATED

    def test_get_sources(self):
        self.pt.record_derivation("k6", "src1", "t")
        self.pt.record_derivation("k6", "src2", "t")
        sources = self.pt.get_sources("k6")
        assert set(sources) == {"src1", "src2"}

    def test_has_provenance(self):
        assert not self.pt.has_provenance("k7")
        self.pt.record_creation("k7")
        assert self.pt.has_provenance("k7")

    def test_record_count(self):
        self.pt.record_creation("k8")
        self.pt.record_creation("k8")
        assert self.pt.record_count("k8") == 2

    def test_get_record_by_id(self):
        pr = self.pt.record_creation("k9")
        fetched = self.pt.get_record(pr.provenance_id)
        assert fetched.provenance_id == pr.provenance_id

    def test_get_record_missing_raises(self):
        with pytest.raises(ProvenanceError):
            self.pt.get_record("no-such")


# ══════════════════════════════════════════════════════════════════════════════
# 15  TestLineageManager
# ══════════════════════════════════════════════════════════════════════════════

class TestLineageManager:
    def setup_method(self):
        _reset_all()
        self.lm = LineageManager()

    def test_add_edge(self):
        e = self.lm.add_edge("A", "B", LineageRelationType.DERIVED_FROM)
        assert e.source_id == "A"
        assert e.target_id == "B"

    def test_has_edge(self):
        self.lm.add_edge("X", "Y")
        assert self.lm.has_edge("X", "Y")
        assert not self.lm.has_edge("Y", "X")

    def test_cycle_detection(self):
        self.lm.add_edge("A", "B")
        self.lm.add_edge("B", "C")
        with pytest.raises(LineageCycleError):
            self.lm.add_edge("C", "A")

    def test_self_loop_raises(self):
        with pytest.raises(LineageCycleError):
            self.lm.add_edge("A", "A")

    def test_get_descendants(self):
        self.lm.add_edge("root", "child1")
        self.lm.add_edge("child1", "grandchild1")
        desc = self.lm.get_descendants("root")
        assert "child1" in desc
        assert "grandchild1" in desc

    def test_get_ancestors(self):
        self.lm.add_edge("parent", "child")
        self.lm.add_edge("grandparent", "parent")
        anc = self.lm.get_ancestors("child")
        assert "parent" in anc
        assert "grandparent" in anc

    def test_get_lineage_graph(self):
        self.lm.add_edge("root", "c1")
        self.lm.add_edge("root", "c2")
        graph = self.lm.get_lineage("root", depth=2)
        assert graph.root_id == "root"
        assert graph.node_count >= 3

    def test_remove_edge(self):
        self.lm.add_edge("A", "B")
        self.lm.remove_edge("A", "B")
        assert not self.lm.has_edge("A", "B")

    def test_impact_analysis(self):
        self.lm.add_edge("A", "B")
        self.lm.add_edge("A", "C")
        impact = self.lm.impact_analysis("A")
        assert impact["total_downstream"] >= 2

    def test_duplicate_edge_ignored(self):
        self.lm.add_edge("A", "B")
        self.lm.add_edge("A", "B")  # duplicate — should not raise
        # only one outgoing edge
        with self.lm._lock:
            count = sum(1 for (t, r, _) in self.lm._outgoing.get("A", [])
                        if t == "B")
        assert count == 1

    def test_statistics(self):
        self.lm.add_edge("A", "B")
        stats = self.lm.statistics()
        assert stats["total_edges"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 16  TestDependencyTracker
# ══════════════════════════════════════════════════════════════════════════════

class TestDependencyTracker:
    def setup_method(self):
        _reset_all()
        lm = LineageManager()
        self.dt = DependencyTracker(lm)

    def test_add_dependency(self):
        self.dt.add_dependency("app", "lib")
        assert self.dt.has_dependency("app", "lib")

    def test_get_dependencies(self):
        self.dt.add_dependency("a", "b")
        self.dt.add_dependency("a", "c")
        deps = self.dt.get_dependencies("a")
        assert set(deps) == {"b", "c"}

    def test_get_dependents(self):
        self.dt.add_dependency("x", "y")
        dependents = self.dt.get_dependents("y")
        assert "x" in dependents

    def test_remove_dependency(self):
        self.dt.add_dependency("p", "q")
        self.dt.remove_dependency("p", "q")
        assert not self.dt.has_dependency("p", "q")

    def test_transitive_dependencies(self):
        self.dt.add_dependency("a", "b")
        self.dt.add_dependency("b", "c")
        trans = self.dt.transitive_dependencies("a")
        assert "b" in trans
        assert "c" in trans


# ══════════════════════════════════════════════════════════════════════════════
# 17  TestVersionContext
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionContext:
    def setup_method(self):
        _reset_all()
        self.ctx = VersionContext()

    def test_default_actor(self):
        assert self.ctx.actor == SYSTEM_VERSIONING_ACTOR

    def test_set_actor(self):
        self.ctx.actor = "user:alice"
        assert self.ctx.actor == "user:alice"

    def test_operation_context_manager(self):
        with self.ctx.operation(actor="user:bob", operation_id="op-1"):
            assert self.ctx.actor == "user:bob"
            assert self.ctx.operation_id == "op-1"
        # Restored after context
        assert self.ctx.actor == SYSTEM_VERSIONING_ACTOR

    def test_module_level_helpers(self):
        with version_operation(actor="user:carol"):
            assert current_version_actor() == "user:carol"
        assert current_version_actor() == SYSTEM_VERSIONING_ACTOR

    def test_thread_local_isolation(self):
        results: list[str] = []

        def thread_fn() -> None:
            with version_operation(actor="user:thread"):
                results.append(current_version_actor())

        t = threading.Thread(target=thread_fn)
        t.start()
        t.join()
        assert results == ["user:thread"]
        # Main thread unaffected
        assert current_version_actor() == SYSTEM_VERSIONING_ACTOR


# ══════════════════════════════════════════════════════════════════════════════
# 18  TestVersionFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionFactory:
    def setup_method(self):
        _reset_all()
        self.f = VersionFactory()

    def test_create_version(self):
        kv = self.f.create_version("kid", "2.0.0", 3, author="user:a")
        assert kv.version_string == "2.0.0"
        assert kv.author == "user:a"

    def test_create_draft(self):
        kv = self.f.create_draft("kid", "1.0.0", 1)
        assert kv.status == VersionStatus.DRAFT

    def test_create_branch(self):
        b = self.f.create_branch("kid", "feature/test")
        assert b.name == "feature/test"
        assert b.source_branch == DEFAULT_BRANCH

    def test_create_experimental_branch(self):
        b = self.f.create_experimental_branch("kid", "algo-v2")
        assert b.name == "experimental/algo-v2"

    def test_create_working_branch(self):
        b = self.f.create_working_branch("kid", "fix-123")
        assert b.name == "work/fix-123"

    def test_create_provenance_creation(self):
        pr = self.f.create_provenance_creation("kid", actor="user:alice")
        assert pr.provenance_type == ProvenanceType.CREATED
        assert pr.actor == "user:alice"

    def test_create_provenance_derivation(self):
        pr = self.f.create_provenance_derivation("kid", "src-id", "filter")
        assert pr.provenance_type == ProvenanceType.DERIVED_FROM
        assert pr.source_id == "src-id"
        assert pr.transformation == "filter"

    def test_create_lineage_edge(self):
        e = self.f.create_lineage_edge("A", "B", LineageRelationType.DEPENDS_ON)
        assert e.source_id == "A"
        assert e.relation == LineageRelationType.DEPENDS_ON

    def test_singleton(self):
        f1 = get_version_factory()
        f2 = get_version_factory()
        assert f1 is f2


# ══════════════════════════════════════════════════════════════════════════════
# 19  TestVersionEngine  (integration)
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionEngine:
    def setup_method(self):
        _reset_all()
        self.ve = VersionEngine()

    def test_create_version_returns_knowledge_version(self):
        record = _make_record("Facts")
        v = self.ve.create_version(record, VersionBump.MINOR, author="user:test")
        assert isinstance(v, KnowledgeVersion)
        assert v.version_string == "1.1.0"

    def test_history_populated_after_create(self):
        record = _make_record()
        self.ve.create_version(record, VersionBump.MINOR)
        h = self.ve.history(record.id)
        assert h.count == 1

    def test_get_version(self):
        record = _make_record()
        v = self.ve.create_version(record)
        fetched = self.ve.get_version(v.version_id)
        assert fetched.version_id == v.version_id

    def test_get_latest(self):
        record = _make_record()
        v1 = self.ve.create_version(record, VersionBump.MINOR)
        v2 = self.ve.create_version(record, VersionBump.MINOR)
        latest = self.ve.get_latest(record.id)
        assert latest.version_id == v2.version_id

    def test_release_version(self):
        record = _make_record()
        v = self.ve.create_version(record)
        released = self.ve.release_version(v.version_id, actor="user:pm")
        assert released.status == VersionStatus.RELEASED
        # Check audit entry was created
        trail = self.ve.audit_trail(record.id,
                                    event_type=VersionEventType.VERSION_RELEASED)
        assert len(trail) >= 1

    def test_archive_version(self):
        record = _make_record()
        v = self.ve.create_version(record)
        archived = self.ve.archive_version(v.version_id)
        assert archived.status == VersionStatus.ARCHIVED

    def test_promote_draft(self):
        record = _make_record()
        v = self.ve.create_version(record, is_draft=True)
        assert v.status == VersionStatus.DRAFT
        promoted = self.ve.promote_draft(v.version_id)
        assert promoted.status == VersionStatus.CURRENT

    def test_rollback_restores_record(self):
        record = _make_record("Original")
        v1 = self.ve.create_version(record, VersionBump.MINOR)
        record.title = "Updated"
        self.ve.create_version(record, VersionBump.MINOR)
        record, rollback_v = self.ve.rollback(record, v1.version_id,
                                               author="user:bob")
        assert record.title == "Original"
        # Audit entry
        trail = self.ve.audit_trail(record.id,
                                    event_type=VersionEventType.ROLLBACK)
        assert len(trail) >= 1

    def test_create_branch(self):
        record = _make_record()
        self.ve.create_version(record)
        branch = self.ve.create_branch(record.id, "experimental/test",
                                        author="user:dev")
        assert branch.name == "experimental/test"

    def test_list_branches(self):
        record = _make_record()
        self.ve.create_version(record)
        self.ve.create_branch(record.id, "feature/a")
        branches = self.ve.list_branches(record.id)
        names = [b.name for b in branches]
        assert "feature/a" in names

    def test_merge_branch(self):
        record = _make_record("Base")
        v1 = self.ve.create_version(record, VersionBump.MINOR)
        self.ve.create_branch(record.id, "feature/merge-test",
                               source_version_id=v1.version_id)
        record.title = "Feature Title"
        self.ve.create_version(record, VersionBump.MINOR, branch="feature/merge-test")
        result = self.ve.merge_branch(
            record.id, "feature/merge-test", "main",
            strategy=MergeStrategy.THEIRS, author="user:merge"
        )
        assert result.success
        assert result.new_version_id is not None

    def test_diff(self):
        record = _make_record("Old")
        v1 = self.ve.create_version(record, VersionBump.SNAPSHOT)
        record.title = "New"
        v2 = self.ve.create_version(record, VersionBump.MINOR)
        diff = self.ve.diff(record.id, v1.version_id, v2.version_id)
        assert "title" in diff.changed_fields

    def test_record_provenance_and_retrieve(self):
        record = _make_record()
        self.ve.create_version(record)
        self.ve.record_provenance(
            record.id, ProvenanceType.DERIVED_FROM,
            actor     = "user:x",
            source_id = "other-id",
        )
        prv = self.ve.provenance(record.id)
        assert len(prv) >= 1

    def test_link_lineage(self):
        self.ve.link_lineage("A", "B", LineageRelationType.DERIVED_FROM)
        graph = self.ve.lineage("A")
        ids = graph.all_node_ids()
        assert "A" in ids

    def test_impact_analysis(self):
        self.ve.link_lineage("root", "child1")
        self.ve.link_lineage("root", "child2")
        impact = self.ve.impact_analysis("root")
        assert impact["total_downstream"] >= 2

    def test_audit_trail(self):
        record = _make_record()
        v = self.ve.create_version(record, author="user:audit-test")
        self.ve.release_version(v.version_id, actor="user:audit-test")
        trail = self.ve.audit_trail(record.id)
        assert len(trail) >= 2

    def test_statistics(self):
        record = _make_record()
        self.ve.create_version(record)
        stats = self.ve.statistics()
        assert "version_manager" in stats
        assert "branch_manager" in stats
        assert "audit_log" in stats

    def test_status(self):
        record = _make_record()
        self.ve.create_version(record)
        s = self.ve.status()
        assert s["status"] == "healthy"
        assert s["total_versions"] >= 1

    def test_create_version_with_provenance(self):
        record = _make_record()
        self.ve.create_version(
            record,
            track_provenance = True,
            author           = "user:a",
        )
        prv = self.ve.provenance(record.id)
        assert any(p.provenance_type == ProvenanceType.CREATED for p in prv)

    def test_singleton(self):
        e1 = get_version_engine()
        e2 = get_version_engine()
        assert e1 is e2


# ══════════════════════════════════════════════════════════════════════════════
# 20  TestVersionRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionRegistry:
    def setup_method(self):
        _reset_all()
        self.reg = VersionRegistry()

    def test_get_version_engine(self):
        ve = self.reg.get("version_engine")
        assert isinstance(ve, VersionEngine)

    def test_get_version_manager(self):
        vm = self.reg.get("version_manager")
        assert isinstance(vm, VersionManager)

    def test_get_audit_log(self):
        al = self.reg.get("audit_log")
        assert isinstance(al, AuditLog)

    def test_register_custom(self):
        self.reg.register("custom_svc", object())
        assert self.reg.has("custom_svc")

    def test_get_missing_raises(self):
        _ = self.reg.names()  # trigger auto-register
        with pytest.raises(KeyError):
            self.reg.get("no_such_component")

    def test_names_includes_all_defaults(self):
        names = self.reg.names()
        for expected in ["version_engine", "branch_manager", "diff_engine",
                         "audit_log", "provenance_tracker", "lineage_manager"]:
            assert expected in names

    def test_status(self):
        s = self.reg.status()
        assert s["count"] >= 10
        assert s["initialised"]

    def test_singleton(self):
        r1 = get_version_registry()
        r2 = get_version_registry()
        assert r1 is r2
