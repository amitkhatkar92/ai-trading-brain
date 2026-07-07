"""
iios/knowledge/versioning/version_engine.py
============================================
VersionEngine — high-level façade that coordinates all versioning
subsystems (VersionManager, BranchManager, DiffEngine, AuditLog,
ProvenanceTracker, LineageManager) behind a single public API.

This is the primary entry-point for callers.

Usage::

    from iios.knowledge.versioning.version_engine import get_version_engine
    from iios.knowledge.knowledge_constants import VersionBump

    engine = get_version_engine()

    # Create a version
    v = engine.create_version(record, VersionBump.MINOR, author="user:alice",
                               reason="Updated content")

    # Create a branch
    b = engine.create_branch(record.id, "experimental/new-strategy",
                              source_version_id=v.version_id)

    # Compute diff
    diff = engine.diff(record.id, v1_id, v2_id)

    # Rollback
    record, rollback_ver = engine.rollback(record, v1_id,
                                            author="user:bob", reason="Reverted")

    # Lineage
    graph = engine.lineage(record.id, depth=3)

    # Audit trail
    trail = engine.audit_trail(record.id)
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from ..knowledge_constants import VersionBump
from ..models.knowledge_record import KnowledgeRecord
from .version_constants import (
    DEFAULT_BRANCH,
    MergeStrategy,
    ProvenanceType,
    VersionEventType,
    LineageRelationType,
    SYSTEM_VERSIONING_ACTOR,
)
from .version_exceptions import VersionEngineError
from .version_manager   import VersionManager, get_version_manager
from .branch_manager    import BranchManager, get_branch_manager
from .diff_engine       import DiffEngine, get_diff_engine
from .audit_log         import AuditLog, get_audit_log
from .provenance_tracker import ProvenanceTracker, get_provenance_tracker
from .lineage_manager   import LineageManager, get_lineage_manager
from .models.knowledge_version import KnowledgeVersion, VersionStatus
from .models.version_history   import VersionHistory
from .models.version_branch    import VersionBranch, MergeResult
from .models.version_diff      import RecordDiff
from .models.version_audit     import AuditEntry
from .models.provenance_record import ProvenanceRecord
from .models.lineage_graph     import LineageEdge, LineageGraph

__all__ = ["VersionEngine", "get_version_engine", "reset_version_engine"]

_LOG = logging.getLogger("iios.knowledge.versioning.engine")
_lock = threading.Lock()
_engine: Optional["VersionEngine"] = None


class VersionEngine:
    """High-level versioning façade.

    All subsystems are injected at construction; module-level singletons
    are used as defaults so callers do not need to wire anything.
    """

    def __init__(
        self,
        version_manager:   Optional[VersionManager]    = None,
        branch_manager:    Optional[BranchManager]     = None,
        diff_engine:       Optional[DiffEngine]        = None,
        audit_log:         Optional[AuditLog]          = None,
        provenance_tracker:Optional[ProvenanceTracker] = None,
        lineage_manager:   Optional[LineageManager]    = None,
    ) -> None:
        self._vm  = version_manager    or get_version_manager()
        self._bm  = branch_manager     or get_branch_manager()
        self._de  = diff_engine        or get_diff_engine()
        self._al  = audit_log          or get_audit_log()
        self._pt  = provenance_tracker or get_provenance_tracker()
        self._lm  = lineage_manager    or get_lineage_manager()

    # ── Version creation ──────────────────────────────────────────────────────

    def create_version(
        self,
        record:         KnowledgeRecord,
        bump:           VersionBump = VersionBump.MINOR,
        author:         str = SYSTEM_VERSIONING_ACTOR,
        reason:         str = "",
        change_summary: str = "",
        branch:         str = DEFAULT_BRANCH,
        tags:           Optional[list[str]] = None,
        is_draft:       bool = False,
        track_provenance: bool = False,
        source_id:      Optional[str] = None,
        transformation: str = "",
    ) -> KnowledgeVersion:
        """Create a new version for *record*.

        Optionally records creation / derivation provenance when
        ``track_provenance=True``.
        """
        kv = self._vm.create_version(
            record         = record,
            bump           = bump,
            author         = author,
            change_summary = change_summary,
            change_reason  = reason,
            branch         = branch,
            tags           = tags,
            is_draft       = is_draft,
        )

        # Register version on branch (auto-creates main branch if needed)
        try:
            self._bm.register_version(record.id, branch, kv.version_id)
        except Exception:
            self._bm.ensure_main_branch(record.id, kv.version_id)
            if branch != DEFAULT_BRANCH:
                self._bm.register_version(record.id, branch, kv.version_id)
            else:
                self._bm.register_version(record.id, DEFAULT_BRANCH, kv.version_id)

        # Audit
        self._al.log(
            knowledge_id = record.id,
            event_type   = VersionEventType.VERSION_CREATED,
            actor        = author,
            reason       = reason,
            version_id   = kv.version_id,
            branch_name  = branch,
            details      = {"bump": bump.value, "version_string": kv.version_string},
        )

        # Provenance
        if track_provenance:
            if source_id:
                self._pt.record_derivation(
                    record.id, source_id, transformation, actor=author
                )
            else:
                self._pt.record_creation(record.id, actor=author)

            self._al.log(
                knowledge_id = record.id,
                event_type   = VersionEventType.PROVENANCE_LINKED,
                actor        = author,
                version_id   = kv.version_id,
                branch_name  = branch,
            )

        _LOG.info(
            "VersionEngine: created v%s (seq=%d) on '%s' for '%s'",
            kv.version_string, kv.version_seq, branch, record.id[:16],
        )
        return kv

    # ── History ───────────────────────────────────────────────────────────────

    def history(
        self,
        knowledge_id: str,
        branch:       Optional[str] = None,
    ) -> VersionHistory:
        """Return ordered version history for *knowledge_id*."""
        versions = self._vm.list_versions(knowledge_id, branch=branch)
        return VersionHistory(
            knowledge_id = knowledge_id,
            branch       = branch or DEFAULT_BRANCH,
            versions     = versions,
        )

    def get_version(self, version_id: str) -> KnowledgeVersion:
        return self._vm.get(version_id)

    def get_latest(
        self, knowledge_id: str, branch: str = DEFAULT_BRANCH
    ) -> Optional[KnowledgeVersion]:
        return self._vm.get_latest(knowledge_id, branch=branch)

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def release_version(
        self,
        version_id: str,
        actor:      str = SYSTEM_VERSIONING_ACTOR,
        reason:     str = "",
    ) -> KnowledgeVersion:
        kv = self._vm.release(version_id)
        self._al.log(
            knowledge_id = kv.knowledge_id,
            event_type   = VersionEventType.VERSION_RELEASED,
            actor        = actor,
            reason       = reason,
            version_id   = version_id,
            branch_name  = kv.branch_name,
        )
        return kv

    def archive_version(
        self,
        version_id: str,
        actor:      str = SYSTEM_VERSIONING_ACTOR,
    ) -> KnowledgeVersion:
        kv = self._vm.archive(version_id)
        self._al.log(
            knowledge_id = kv.knowledge_id,
            event_type   = VersionEventType.VERSION_ARCHIVED,
            actor        = actor,
            version_id   = version_id,
            branch_name  = kv.branch_name,
        )
        return kv

    def promote_draft(
        self,
        version_id: str,
        actor:      str = SYSTEM_VERSIONING_ACTOR,
    ) -> KnowledgeVersion:
        kv = self._vm.promote_draft(version_id)
        self._al.log(
            knowledge_id = kv.knowledge_id,
            event_type   = VersionEventType.DRAFT_PROMOTED,
            actor        = actor,
            version_id   = version_id,
            branch_name  = kv.branch_name,
        )
        return kv

    # ── Rollback ──────────────────────────────────────────────────────────────

    def rollback(
        self,
        record:            KnowledgeRecord,
        target_version_id: str,
        author:            str = SYSTEM_VERSIONING_ACTOR,
        reason:            str = "",
        branch:            str = DEFAULT_BRANCH,
    ) -> tuple[KnowledgeRecord, KnowledgeVersion]:
        """Restore *record* to a prior version.

        Returns (mutated record, new rollback KnowledgeVersion).
        """
        record, kv = self._vm.rollback(
            record,
            target_version_id,
            rolled_back_by = author,
            reason         = reason,
            branch         = branch,
        )
        # Register on branch
        try:
            self._bm.register_version(record.id, branch, kv.version_id)
        except Exception:
            pass

        self._al.log(
            knowledge_id = record.id,
            event_type   = VersionEventType.ROLLBACK,
            actor        = author,
            reason       = reason,
            version_id   = kv.version_id,
            branch_name  = branch,
            details      = {"rolled_back_to": target_version_id},
        )
        _LOG.info(
            "VersionEngine: rollback '%s' → %s",
            record.id[:16], target_version_id[:8],
        )
        return record, kv

    # ── Branching ─────────────────────────────────────────────────────────────

    def create_branch(
        self,
        knowledge_id:      str,
        name:              str,
        source_branch:     str = DEFAULT_BRANCH,
        source_version_id: Optional[str] = None,
        author:            str = SYSTEM_VERSIONING_ACTOR,
        description:       str = "",
    ) -> VersionBranch:
        # Resolve source_version_id if not supplied
        if source_version_id is None:
            src_latest = self._vm.get_latest(knowledge_id, branch=source_branch)
            if src_latest:
                source_version_id = src_latest.version_id

        branch = self._bm.create_branch(
            knowledge_id      = knowledge_id,
            name              = name,
            source_branch     = source_branch,
            source_version_id = source_version_id,
            created_by        = author,
            description       = description,
        )
        self._al.log(
            knowledge_id = knowledge_id,
            event_type   = VersionEventType.BRANCH_CREATED,
            actor        = author,
            branch_name  = name,
            details      = {"source_branch": source_branch,
                            "source_version": source_version_id},
        )
        return branch

    def merge_branch(
        self,
        knowledge_id:  str,
        source_branch: str,
        target_branch: str = DEFAULT_BRANCH,
        strategy:      MergeStrategy = MergeStrategy.THEIRS,
        author:        str = SYSTEM_VERSIONING_ACTOR,
        reason:        str = "",
    ) -> MergeResult:
        result = self._bm.merge(
            knowledge_id   = knowledge_id,
            source_branch  = source_branch,
            target_branch  = target_branch,
            strategy       = strategy,
            merged_by      = author,
            version_manager = self._vm,
            diff_engine    = self._de,
        )
        if result.success:
            self._al.log(
                knowledge_id = knowledge_id,
                event_type   = VersionEventType.BRANCH_MERGED,
                actor        = author,
                reason       = reason,
                version_id   = result.new_version_id,
                branch_name  = target_branch,
                details      = {
                    "source_branch":    source_branch,
                    "strategy":         strategy.value,
                    "conflict_count":   len(result.conflicts),
                },
            )
            # Record merge provenance
            if result.new_version_id:
                src_latest = self._bm.get(knowledge_id, source_branch)
                if src_latest.head_version_id:
                    self._pt.record_merge(
                        knowledge_id,
                        source_ids = [knowledge_id],  # same item, different branch
                        actor      = author,
                    )
        return result

    def list_branches(self, knowledge_id: str) -> list[VersionBranch]:
        return self._bm.list_branches(knowledge_id)

    def get_branch(self, knowledge_id: str, name: str) -> VersionBranch:
        return self._bm.get(knowledge_id, name)

    # ── Diff ──────────────────────────────────────────────────────────────────

    def diff(
        self,
        knowledge_id:  str,
        version_id_v1: str,
        version_id_v2: str,
    ) -> RecordDiff:
        v1 = self._vm.get(version_id_v1)
        v2 = self._vm.get(version_id_v2)
        return self._de.compute_diff(knowledge_id, v1, v2)

    def diff_with_latest(
        self,
        knowledge_id: str,
        version_id:   str,
        branch:       str = DEFAULT_BRANCH,
    ) -> Optional[RecordDiff]:
        v1 = self._vm.get(version_id)
        v2 = self._vm.get_latest(knowledge_id, branch=branch)
        if v2 is None:
            return None
        return self._de.compute_diff(knowledge_id, v1, v2)

    # ── Provenance ────────────────────────────────────────────────────────────

    def record_provenance(
        self,
        knowledge_id:    str,
        provenance_type: ProvenanceType,
        actor:           str = SYSTEM_VERSIONING_ACTOR,
        description:     str = "",
        source_id:       Optional[str] = None,
        transformation:  str = "",
    ) -> ProvenanceRecord:
        pr = self._pt.record(
            knowledge_id    = knowledge_id,
            provenance_type = provenance_type,
            actor           = actor,
            description     = description,
            source_id       = source_id,
            transformation  = transformation,
        )
        self._al.log(
            knowledge_id = knowledge_id,
            event_type   = VersionEventType.PROVENANCE_LINKED,
            actor        = actor,
            details      = {"provenance_type": provenance_type.value,
                            "source_id": source_id},
        )
        return pr

    def provenance(
        self,
        knowledge_id:    str,
        provenance_type: Optional[ProvenanceType] = None,
    ) -> list[ProvenanceRecord]:
        return self._pt.get_provenance(knowledge_id, provenance_type)

    # ── Lineage ───────────────────────────────────────────────────────────────

    def link_lineage(
        self,
        source_id: str,
        target_id: str,
        relation:  LineageRelationType = LineageRelationType.DERIVED_FROM,
        weight:    float = 1.0,
        actor:     str = SYSTEM_VERSIONING_ACTOR,
    ) -> LineageEdge:
        edge = self._lm.add_edge(source_id, target_id, relation, weight)
        self._al.log(
            knowledge_id = source_id,
            event_type   = VersionEventType.LINEAGE_LINKED,
            actor        = actor,
            details      = {"target_id": target_id, "relation": relation.value},
        )
        return edge

    def lineage(self, knowledge_id: str, depth: int = 3) -> LineageGraph:
        return self._lm.get_lineage(knowledge_id, depth=depth)

    def impact_analysis(self, knowledge_id: str) -> dict[str, Any]:
        return self._lm.impact_analysis(knowledge_id)

    # ── Audit ─────────────────────────────────────────────────────────────────

    def audit_trail(
        self,
        knowledge_id: str,
        event_type:   Optional[VersionEventType] = None,
        limit:        Optional[int] = None,
    ) -> list[AuditEntry]:
        return self._al.get_trail(knowledge_id, event_type=event_type, limit=limit)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        return {
            "version_manager":    self._vm.statistics(),
            "branch_manager":     self._bm.statistics(),
            "audit_log":          self._al.statistics(),
            "provenance_tracker": self._pt.statistics(),
            "lineage_manager":    self._lm.statistics(),
        }

    def status(self) -> dict[str, Any]:
        stats = self.statistics()
        return {
            "status":          "healthy",
            "total_versions":  stats["version_manager"]["total_versions"],
            "unique_items":    stats["version_manager"]["unique_items"],
            "total_branches":  stats["branch_manager"]["total_branches"],
            "total_audit":     stats["audit_log"]["total_entries"],
            "provenance":      stats["provenance_tracker"]["total_records"],
            "lineage_edges":   stats["lineage_manager"]["total_edges"],
        }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_version_engine() -> VersionEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = VersionEngine()
    return _engine


def reset_version_engine() -> None:
    global _engine
    with _lock:
        _engine = None
