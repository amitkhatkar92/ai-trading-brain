"""
iios/knowledge/versioning/branch_manager.py
============================================
BranchManager — creates, tracks, and merges knowledge branches.

Branch metadata (VersionBranch) is stored separately from the actual
version objects (which live in VersionManager).  The BranchManager
assigns new versions to their branch and executes merge strategies.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from ..knowledge_constants import VersionBump
from .version_constants import (
    BranchStatus,
    MergeStrategy,
    VersionEventType,
    DEFAULT_BRANCH,
    SYSTEM_VERSIONING_ACTOR,
)
from .version_exceptions import (
    BranchAlreadyExistsError,
    BranchConflictError,
    BranchMergeError,
    BranchNotFoundError,
)
from .models.knowledge_version import KnowledgeVersion, VersionStatus
from .models.version_branch import VersionBranch, ConflictInfo, MergeResult

__all__ = ["BranchManager", "get_branch_manager", "reset_branch_manager"]

_LOG = logging.getLogger("iios.knowledge.versioning.branch")
_lock = threading.Lock()
_manager: Optional["BranchManager"] = None


class BranchManager:
    """Thread-safe manager for knowledge branches."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # "{knowledge_id}:{branch_name}" → VersionBranch
        self._branches: dict[str, VersionBranch] = {}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _key(self, knowledge_id: str, name: str) -> str:
        return f"{knowledge_id}:{name}"

    def _get_or_raise(self, knowledge_id: str, name: str) -> VersionBranch:
        b = self._branches.get(self._key(knowledge_id, name))
        if b is None:
            raise BranchNotFoundError(
                f"Branch '{name}' not found for knowledge item '{knowledge_id}'.",
                code="BM-001",
            )
        return b

    # ── Branch creation ───────────────────────────────────────────────────────

    def create_branch(
        self,
        knowledge_id:      str,
        name:              str,
        source_branch:     str = DEFAULT_BRANCH,
        source_version_id: Optional[str] = None,
        created_by:        str = SYSTEM_VERSIONING_ACTOR,
        description:       str = "",
    ) -> VersionBranch:
        """Create a new branch for *knowledge_id*.

        ``source_version_id`` should be the version ID at the divergence
        point.  If None, the branch is considered to start empty.
        """
        with self._lock:
            key = self._key(knowledge_id, name)
            if key in self._branches:
                raise BranchAlreadyExistsError(
                    f"Branch '{name}' already exists for '{knowledge_id}'.",
                    code="BM-002",
                )
            branch = VersionBranch(
                knowledge_id      = knowledge_id,
                name              = name,
                source_branch     = source_branch,
                source_version_id = source_version_id,
                created_by        = created_by,
                description       = description,
            )
            self._branches[key] = branch

        _LOG.info("Branch created: '%s' for '%s'", name, knowledge_id[:16])
        return branch

    def ensure_main_branch(
        self,
        knowledge_id: str,
        version_id: Optional[str] = None,
    ) -> VersionBranch:
        """Idempotently ensure the main branch record exists."""
        with self._lock:
            key = self._key(knowledge_id, DEFAULT_BRANCH)
            if key not in self._branches:
                branch = VersionBranch(
                    knowledge_id      = knowledge_id,
                    name              = DEFAULT_BRANCH,
                    source_branch     = DEFAULT_BRANCH,
                    source_version_id = version_id,
                    created_by        = SYSTEM_VERSIONING_ACTOR,
                )
                self._branches[key] = branch
            return self._branches[key]

    # ── Version registration ──────────────────────────────────────────────────

    def register_version(
        self,
        knowledge_id: str,
        branch_name:  str,
        version_id:   str,
    ) -> None:
        """Attach a version_id to a branch's commit list."""
        with self._lock:
            try:
                branch = self._get_or_raise(knowledge_id, branch_name)
            except BranchNotFoundError:
                # Auto-create branch if it is the main branch
                if branch_name == DEFAULT_BRANCH:
                    branch = self.ensure_main_branch(knowledge_id)
                else:
                    raise
            branch.add_version(version_id)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, knowledge_id: str, name: str) -> VersionBranch:
        with self._lock:
            return self._get_or_raise(knowledge_id, name)

    def exists(self, knowledge_id: str, name: str) -> bool:
        with self._lock:
            return self._key(knowledge_id, name) in self._branches

    def list_branches(self, knowledge_id: str) -> list[VersionBranch]:
        with self._lock:
            prefix = f"{knowledge_id}:"
            return [b for k, b in self._branches.items() if k.startswith(prefix)]

    def open_branches(self, knowledge_id: str) -> list[VersionBranch]:
        return [b for b in self.list_branches(knowledge_id)
                if b.status == BranchStatus.OPEN]

    # ── Merge ─────────────────────────────────────────────────────────────────

    def merge(
        self,
        knowledge_id:  str,
        source_branch: str,
        target_branch: str,
        strategy:      MergeStrategy,
        merged_by:     str = SYSTEM_VERSIONING_ACTOR,
        *,
        version_manager: Any,  # VersionManager — injected to avoid circular import
        diff_engine:     Any,  # DiffEngine — injected
    ) -> MergeResult:
        """Merge *source_branch* into *target_branch*.

        Returns a MergeResult.  On MANUAL strategy with conflicts, raises
        BranchConflictError.
        """
        with self._lock:
            src = self._get_or_raise(knowledge_id, source_branch)
            tgt = self._get_or_raise(knowledge_id, target_branch)

            if src.status != BranchStatus.OPEN:
                raise BranchMergeError(
                    f"Source branch '{source_branch}' is not open "
                    f"(status: {src.status.value}).",
                    code="BM-010",
                )

            src_vid = src.head_version_id
            tgt_vid = tgt.head_version_id

            if src_vid is None:
                raise BranchMergeError(
                    f"Source branch '{source_branch}' has no versions.",
                    code="BM-011",
                )

        src_ver: KnowledgeVersion = version_manager.get(src_vid)
        tgt_ver: Optional[KnowledgeVersion] = (
            version_manager.get(tgt_vid) if tgt_vid else None
        )

        # ── Compute diffs from ancestor ───────────────────────────────────────
        ancestor_vid: Optional[str] = src.source_version_id
        conflicts: list[ConflictInfo] = []

        if tgt_ver is not None and ancestor_vid is not None:
            try:
                anc_ver: KnowledgeVersion = version_manager.get(ancestor_vid)
                src_diff = diff_engine.compute_diff(
                    knowledge_id, anc_ver, src_ver
                )
                tgt_diff = diff_engine.compute_diff(
                    knowledge_id, anc_ver, tgt_ver
                )
                conflict_fields = diff_engine.detect_conflict_fields(
                    src_diff, tgt_diff
                )
                for field_name in conflict_fields:
                    src_fc = src_diff.get_change(field_name)
                    tgt_fc = tgt_diff.get_change(field_name)
                    anc_fc = anc_ver.payload.get(field_name)
                    conflicts.append(ConflictInfo(
                        field_name   = field_name,
                        source_value = src_fc.after_value if src_fc else None,
                        target_value = tgt_fc.after_value if tgt_fc else None,
                        base_value   = anc_fc,
                    ))
            except Exception as exc:
                _LOG.warning("Conflict detection failed: %s", exc)

        # ── Raise on MANUAL with conflicts ────────────────────────────────────
        if strategy == MergeStrategy.MANUAL and conflicts:
            raise BranchConflictError(
                f"Merge requires manual resolution: "
                f"{len(conflicts)} conflict(s) in fields "
                f"{[c.field_name for c in conflicts]}.",
                conflict_fields=[c.field_name for c in conflicts],
                code="BM-020",
            )

        # ── Resolve payload ───────────────────────────────────────────────────
        merged_payload: dict[str, Any]
        if tgt_ver is None or strategy == MergeStrategy.THEIRS:
            merged_payload = dict(src_ver.payload)
        elif strategy == MergeStrategy.OURS:
            merged_payload = dict(tgt_ver.payload)
        elif strategy == MergeStrategy.LATEST:
            # Use whichever version was created more recently
            merged_payload = (
                dict(src_ver.payload) if src_ver.created_at >= (tgt_ver.created_at if tgt_ver else 0)
                else dict(tgt_ver.payload)
            )
        else:
            merged_payload = dict(src_ver.payload)

        # ── Create merged version on target branch ────────────────────────────
        merge_seq = (tgt_ver.version_seq if tgt_ver else 0) + 1
        merge_ver_str = (tgt_ver.version_string if tgt_ver else src_ver.version_string)

        with self._lock:
            self._demote_current_on_branch(version_manager, knowledge_id, target_branch)

            merged_kv = KnowledgeVersion(
                knowledge_id      = knowledge_id,
                version_string    = merge_ver_str,
                version_seq       = merge_seq,
                bump_type         = VersionBump.MINOR,
                status            = VersionStatus.CURRENT,
                branch_name       = target_branch,
                author            = merged_by,
                change_summary    = (f"Merge '{source_branch}' into "
                                     f"'{target_branch}' ({strategy.value})"),
                change_reason     = "branch merge",
                payload           = merged_payload,
                parent_version_id = tgt_vid,
                merged_from_ids   = [src_vid],
            )
            version_manager.store(merged_kv)

            # Register version on target branch
            tgt = self._branches[self._key(knowledge_id, target_branch)]
            tgt.add_version(merged_kv.version_id)

            # Mark source branch as merged
            src = self._branches[self._key(knowledge_id, source_branch)]
            src.mark_merged(into=target_branch, by=merged_by)

        _LOG.info(
            "Merge complete: '%s' → '%s' (strategy=%s, conflicts=%d)",
            source_branch, target_branch, strategy.value, len(conflicts),
        )
        return MergeResult(
            success        = True,
            knowledge_id   = knowledge_id,
            source_branch  = source_branch,
            target_branch  = target_branch,
            strategy       = strategy,
            new_version_id = merged_kv.version_id,
            conflicts      = conflicts,
            merged_by      = merged_by,
        )

    @staticmethod
    def _demote_current_on_branch(
        version_manager: Any,
        knowledge_id:    str,
        branch_name:     str,
    ) -> None:
        """Archive the existing CURRENT version on a branch before adding a new one."""
        existing = version_manager.list_versions(knowledge_id, branch=branch_name)
        for v in existing:
            if v.status == VersionStatus.CURRENT:
                v.status = VersionStatus.ARCHIVED

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._branches)
            by_status: dict[str, int] = {}
            for b in self._branches.values():
                k = b.status.value
                by_status[k] = by_status.get(k, 0) + 1
            return {
                "total_branches": total,
                "by_status":      by_status,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_branch_manager() -> BranchManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = BranchManager()
    return _manager


def reset_branch_manager() -> None:
    global _manager
    with _lock:
        _manager = None
