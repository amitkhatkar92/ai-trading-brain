"""
iios/knowledge/versioning/version_manager.py
=============================================
VersionManager — central in-memory store for KnowledgeVersion objects.

Responsibilities:
- Create, retrieve, and soft-delete versions.
- Release (publish) and archive versions.
- Rollback: restore a KnowledgeRecord to any prior version.
- Provide ordered version lists per (knowledge_id, branch).

This class owns the canonical version store; all other versioning
subsystems (BranchManager, DiffEngine, …) read from it but do not
write versions directly — they go through VersionManager.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Optional

from ..knowledge_constants import VersionBump, SYSTEM_OWNER
from ..models.knowledge_record import KnowledgeRecord
from .version_constants import (
    DEFAULT_BRANCH,
    MAX_VERSIONS_PER_ITEM,
    SYSTEM_VERSIONING_ACTOR,
)
from .version_exceptions import (
    VersionNotFoundError,
    VersionAlreadyExistsError,
    VersionRollbackError,
    VersionValidationError,
)
from .models.knowledge_version import KnowledgeVersion, VersionStatus

__all__ = ["VersionManager", "get_version_manager", "reset_version_manager"]

_LOG = logging.getLogger("iios.knowledge.versioning.manager")
_lock = threading.Lock()
_manager: Optional["VersionManager"] = None


def _bump(version_string: str, bump: VersionBump) -> str:
    """Compute the next semver string for the given bump type."""
    parts = version_string.split(".")
    if len(parts) != 3:
        return "1.0.0"
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if bump == VersionBump.MAJOR:
        return f"{major + 1}.0.0"
    if bump == VersionBump.MINOR:
        return f"{major}.{minor + 1}.0"
    if bump == VersionBump.PATCH:
        return f"{major}.{minor}.{patch + 1}"
    return version_string   # SNAPSHOT keeps same version string


class VersionManager:
    """Thread-safe store and lifecycle manager for KnowledgeVersion objects."""

    def __init__(self, max_per_item: int = MAX_VERSIONS_PER_ITEM) -> None:
        self._lock = threading.RLock()
        self._max_per_item = max_per_item

        # version_id → KnowledgeVersion
        self._versions: dict[str, KnowledgeVersion] = {}

        # knowledge_id → [version_id, ...] (insertion order, oldest first)
        self._by_knowledge: dict[str, list[str]] = defaultdict(list)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_or_raise(self, version_id: str) -> KnowledgeVersion:
        v = self._versions.get(version_id)
        if v is None:
            raise VersionNotFoundError(
                f"Version '{version_id}' not found", code="VM-001"
            )
        return v

    def _demote_current(self, knowledge_id: str, branch: str) -> None:
        """Mark the existing CURRENT version on this branch as ARCHIVED."""
        for vid in reversed(self._by_knowledge.get(knowledge_id, [])):
            v = self._versions.get(vid)
            if v and v.status == VersionStatus.CURRENT and v.branch_name == branch:
                # Mutate status only — safe because VersionManager owns the store
                object.__setattr__(v, "status", VersionStatus.ARCHIVED)  # type: ignore[arg-type]
                v.status = VersionStatus.ARCHIVED
                break

    # ── Version creation ──────────────────────────────────────────────────────

    def create_version(
        self,
        record: KnowledgeRecord,
        bump: VersionBump = VersionBump.MINOR,
        author: str = SYSTEM_VERSIONING_ACTOR,
        change_summary: str = "",
        change_reason: str = "",
        branch: str = DEFAULT_BRANCH,
        tags: Optional[list[str]] = None,
        attributes: Optional[dict[str, Any]] = None,
        parent_version_id: Optional[str] = None,
        merged_from_ids: Optional[list[str]] = None,
        is_draft: bool = False,
    ) -> KnowledgeVersion:
        """Capture the current state of *record* as a new KnowledgeVersion.

        Bumps the record's ``version`` string and ``version_sequence`` in-place
        (matching the behaviour of the existing KnowledgeVersioningEngine).

        Returns the newly created KnowledgeVersion.
        """
        with self._lock:
            existing = self._by_knowledge.get(record.id, [])
            if len(existing) >= self._max_per_item:
                raise VersionValidationError(
                    f"Knowledge item '{record.id}' has reached the maximum "
                    f"of {self._max_per_item} versions.",
                    code="VM-010",
                )

            # Resolve parent
            if parent_version_id is None and existing:
                parent_version_id = existing[-1]

            # Bump version string & record fields (mutates record)
            new_version_str = _bump(record.version, bump)
            record.version = new_version_str
            record.version_sequence += 1
            record.touch()

            # Demote previous CURRENT on this branch → ARCHIVED
            self._demote_current(record.id, branch)

            status = VersionStatus.DRAFT if is_draft else VersionStatus.CURRENT

            kv = KnowledgeVersion(
                knowledge_id      = record.id,
                version_string    = new_version_str,
                version_seq       = record.version_sequence,
                bump_type         = bump,
                status            = status,
                branch_name       = branch,
                author            = author,
                change_summary    = change_summary,
                change_reason     = change_reason,
                payload           = record.to_dict(),
                parent_version_id = parent_version_id,
                merged_from_ids   = list(merged_from_ids or []),
                tags              = list(tags or []),
                attributes        = dict(attributes or {}),
            )

            self._versions[kv.version_id] = kv
            self._by_knowledge[record.id].append(kv.version_id)

        _LOG.debug(
            "Version created: %s on '%s' v%s seq=%d",
            kv.version_id[:8], branch, new_version_str, record.version_sequence,
        )
        return kv

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, version_id: str) -> KnowledgeVersion:
        with self._lock:
            return self._get_or_raise(version_id)

    def get_latest(
        self,
        knowledge_id: str,
        branch: str = DEFAULT_BRANCH,
    ) -> Optional[KnowledgeVersion]:
        with self._lock:
            for vid in reversed(self._by_knowledge.get(knowledge_id, [])):
                v = self._versions.get(vid)
                if v and v.branch_name == branch and v.status not in (
                    VersionStatus.DELETED,
                ):
                    return v
        return None

    def list_versions(
        self,
        knowledge_id: str,
        branch: Optional[str] = None,
        include_deleted: bool = False,
    ) -> list[KnowledgeVersion]:
        with self._lock:
            result: list[KnowledgeVersion] = []
            for vid in self._by_knowledge.get(knowledge_id, []):
                v = self._versions.get(vid)
                if v is None:
                    continue
                if not include_deleted and v.status == VersionStatus.DELETED:
                    continue
                if branch is not None and v.branch_name != branch:
                    continue
                result.append(v)
            return result

    def version_count(self, knowledge_id: str) -> int:
        with self._lock:
            return len(self._by_knowledge.get(knowledge_id, []))

    def exists(self, version_id: str) -> bool:
        with self._lock:
            return version_id in self._versions

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def release(self, version_id: str) -> KnowledgeVersion:
        """Promote a DRAFT or CURRENT version to RELEASED (frozen)."""
        with self._lock:
            v = self._get_or_raise(version_id)
            if v.status not in (VersionStatus.DRAFT, VersionStatus.CURRENT):
                raise VersionValidationError(
                    f"Cannot release version '{version_id}' "
                    f"(current status: {v.status.value}).",
                    code="VM-020",
                )
            v.status = VersionStatus.RELEASED
        _LOG.info("Version released: %s", version_id[:8])
        return v

    def archive(self, version_id: str) -> KnowledgeVersion:
        """Move a version to ARCHIVED."""
        with self._lock:
            v = self._get_or_raise(version_id)
            v.status = VersionStatus.ARCHIVED
        return v

    def soft_delete(self, version_id: str) -> KnowledgeVersion:
        """Soft-delete a version (payload is retained)."""
        with self._lock:
            v = self._get_or_raise(version_id)
            v.status = VersionStatus.DELETED
        _LOG.info("Version soft-deleted: %s", version_id[:8])
        return v

    def promote_draft(self, version_id: str) -> KnowledgeVersion:
        """Promote a DRAFT version to CURRENT."""
        with self._lock:
            v = self._get_or_raise(version_id)
            if v.status != VersionStatus.DRAFT:
                raise VersionValidationError(
                    f"Version '{version_id}' is not a draft.",
                    code="VM-025",
                )
            # Demote existing CURRENT on the same branch
            self._demote_current(v.knowledge_id, v.branch_name)
            v.status = VersionStatus.CURRENT
        return v

    # ── Rollback ──────────────────────────────────────────────────────────────

    def rollback(
        self,
        record: KnowledgeRecord,
        target_version_id: str,
        rolled_back_by: str = SYSTEM_OWNER,
        reason: str = "",
        branch: str = DEFAULT_BRANCH,
    ) -> tuple[KnowledgeRecord, KnowledgeVersion]:
        """Restore *record* to the state captured in *target_version_id*.

        Creates a new KnowledgeVersion with status=ROLLBACK on *branch*
        and mutates *record* in-place.  Returns (record, new_version).
        """
        with self._lock:
            target = self._get_or_raise(target_version_id)

        try:
            restored = KnowledgeRecord.from_dict(target.payload)
        except Exception as exc:
            raise VersionRollbackError(
                f"Failed to deserialise version '{target_version_id}': {exc}",
                code="VM-030",
            ) from exc

        with self._lock:
            # Apply payload to record
            record.title           = restored.title
            record.content         = restored.content
            record.status          = restored.status
            record.metadata        = restored.metadata
            record.references      = restored.references
            record.version         = restored.version
            record.version_sequence = restored.version_sequence + 1
            record.touch()

            # Find previous CURRENT on branch
            parent_vid = None
            for vid in reversed(self._by_knowledge.get(record.id, [])):
                v = self._versions.get(vid)
                if v and v.branch_name == branch:
                    parent_vid = vid
                    break

            self._demote_current(record.id, branch)

            kv = KnowledgeVersion(
                knowledge_id      = record.id,
                version_string    = record.version,
                version_seq       = record.version_sequence,
                bump_type         = VersionBump.SNAPSHOT,
                status            = VersionStatus.ROLLBACK,
                branch_name       = branch,
                author            = rolled_back_by,
                change_summary    = f"Rollback to version {target_version_id[:8]}",
                change_reason     = reason,
                payload           = record.to_dict(),
                parent_version_id = parent_vid,
                attributes        = {"rolled_back_to": target_version_id},
            )
            self._versions[kv.version_id] = kv
            self._by_knowledge[record.id].append(kv.version_id)

        _LOG.info(
            "Rollback: %s → version %s (new version_id=%s)",
            record.id, target_version_id[:8], kv.version_id[:8],
        )
        return record, kv

    # ── Direct version store (used by BranchManager after merge) ─────────────

    def store(self, kv: KnowledgeVersion) -> None:
        """Directly store a KnowledgeVersion (used by merge operations)."""
        with self._lock:
            if kv.version_id in self._versions:
                raise VersionAlreadyExistsError(
                    f"Version '{kv.version_id}' already stored.", code="VM-040"
                )
            self._demote_current(kv.knowledge_id, kv.branch_name)
            self._versions[kv.version_id] = kv
            self._by_knowledge[kv.knowledge_id].append(kv.version_id)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._versions)
            by_status: dict[str, int] = {}
            for v in self._versions.values():
                k = v.status.value
                by_status[k] = by_status.get(k, 0) + 1
            return {
                "total_versions":   total,
                "unique_items":     len(self._by_knowledge),
                "by_status":        by_status,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_version_manager() -> VersionManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = VersionManager()
    return _manager


def reset_version_manager() -> None:
    global _manager
    with _lock:
        _manager = None
