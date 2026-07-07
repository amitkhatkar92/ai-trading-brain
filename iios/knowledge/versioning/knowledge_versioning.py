"""
iios/knowledge/versioning/knowledge_versioning.py
==================================================
Versioning engine: captures snapshots, increments semver, and supports
rollback and history traversal for knowledge records.
"""

from __future__ import annotations

import copy
import logging
import threading
from collections import defaultdict, deque
from typing import Optional

from ..knowledge_constants import (
    VersionBump,
    VersionStatus,
    MAX_SNAPSHOT_HISTORY,
    SYSTEM_OWNER,
)
from ..knowledge_exceptions import (
    KnowledgeVersionError,
    KnowledgeVersionNotFoundError,
    KnowledgeRollbackError,
)
from ..models.knowledge_record import KnowledgeRecord
from ..models.knowledge_snapshot import KnowledgeSnapshot, VersionDiff

__all__ = [
    "KnowledgeVersioningEngine",
    "get_versioning_engine",
    "reset_versioning_engine",
]

_LOG = logging.getLogger("iios.knowledge.versioning")
_lock = threading.Lock()
_engine: Optional["KnowledgeVersioningEngine"] = None


def _bump_version(version: str, bump: VersionBump) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        return "1.0.0"
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if bump == VersionBump.MAJOR:
        return f"{major + 1}.0.0"
    if bump == VersionBump.MINOR:
        return f"{major}.{minor + 1}.0"
    if bump == VersionBump.PATCH:
        return f"{major}.{minor}.{patch + 1}"
    return version   # SNAPSHOT keeps same version


class KnowledgeVersioningEngine:
    """Stores, retrieves and rolls back knowledge record versions.

    Each version is captured as a ``KnowledgeSnapshot``.  The engine
    maintains a bounded deque of snapshots per knowledge item, ordered
    oldest-first.

    Usage::

        engine = get_versioning_engine()
        snapshot = engine.snapshot(record)            # capture current state
        engine.bump_version(record, VersionBump.MINOR)  # increment version
        history = engine.history("iios.knowledge/abc-uuid")
        engine.rollback(record, snapshot.snapshot_id)
    """

    def __init__(self, max_history: int = MAX_SNAPSHOT_HISTORY) -> None:
        self._lock = threading.RLock()
        self._max_history = max_history
        # knowledge_id_full → deque[KnowledgeSnapshot]
        self._history: dict[str, deque[KnowledgeSnapshot]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(
        self,
        record: KnowledgeRecord,
        bump: VersionBump = VersionBump.SNAPSHOT,
        change_summary: str = "",
        created_by: str = SYSTEM_OWNER,
    ) -> KnowledgeSnapshot:
        """Capture the current state of *record* and store it."""
        with self._lock:
            history = self._history[record.id]
            parent_id = history[-1].snapshot_id if history else None

        snap = KnowledgeSnapshot(
            knowledge_id       = record.id,
            version            = record.version,
            version_seq        = record.version_sequence,
            bump_type          = bump,
            status             = VersionStatus.CURRENT,
            created_by         = created_by,
            change_summary     = change_summary,
            payload            = record.to_dict(),
            parent_snapshot_id = parent_id,
        )

        with self._lock:
            # Mark previous current snapshot as historical
            history = self._history[record.id]
            for s in history:
                if s.status == VersionStatus.CURRENT:
                    s.mark_historical()
            history.append(snap)

        _LOG.debug("Snapshot captured: %s v%s seq=%d", record.id, record.version, record.version_sequence)
        return snap

    # ── Version bumping ───────────────────────────────────────────────────────

    def bump_version(
        self,
        record: KnowledgeRecord,
        bump: VersionBump,
        change_summary: str = "",
        created_by: str = SYSTEM_OWNER,
    ) -> KnowledgeSnapshot:
        """Bump *record.version* and capture a snapshot. Mutates the record."""
        if bump == VersionBump.SNAPSHOT:
            return self.snapshot(record, bump, change_summary, created_by)

        new_version = _bump_version(record.version, bump)
        record.previous_version_id = record.id
        record.version = new_version
        record.version_sequence += 1
        record.touch()

        return self.snapshot(record, bump, change_summary, created_by)

    # ── History ───────────────────────────────────────────────────────────────

    def history(self, knowledge_id: str) -> list[KnowledgeSnapshot]:
        """Return full snapshot history for *knowledge_id*, oldest first."""
        with self._lock:
            return list(self._history.get(knowledge_id, []))

    def latest_snapshot(self, knowledge_id: str) -> Optional[KnowledgeSnapshot]:
        with self._lock:
            h = self._history.get(knowledge_id)
            return h[-1] if h else None

    def get_snapshot(self, knowledge_id: str, snapshot_id: str) -> KnowledgeSnapshot:
        with self._lock:
            for snap in self._history.get(knowledge_id, []):
                if snap.snapshot_id == snapshot_id:
                    return snap
        raise KnowledgeVersionNotFoundError(
            f"Snapshot '{snapshot_id}' not found for '{knowledge_id}'",
            code="KVE-001",
        )

    def version_count(self, knowledge_id: str) -> int:
        with self._lock:
            return len(self._history.get(knowledge_id, []))

    # ── Rollback ──────────────────────────────────────────────────────────────

    def rollback(
        self,
        record: KnowledgeRecord,
        snapshot_id: str,
        rolled_back_by: str = SYSTEM_OWNER,
    ) -> KnowledgeRecord:
        """Restore *record* to the state captured in *snapshot_id*.

        Returns the restored record (mutated in-place).
        """
        snap = self.get_snapshot(record.id, snapshot_id)
        try:
            restored = KnowledgeRecord.from_dict(snap.payload)
        except Exception as exc:
            raise KnowledgeRollbackError(
                f"Failed to deserialize snapshot '{snapshot_id}': {exc}",
                code="KVE-002",
            ) from exc

        # Apply restored state to the live record
        record.title           = restored.title
        record.content         = restored.content
        record.status          = restored.status
        record.metadata        = restored.metadata
        record.references      = restored.references
        record.version         = restored.version
        record.version_sequence = restored.version_sequence + 1
        record.previous_version_id = restored.id
        record.touch()

        # Mark the snapshot as rollback
        snap.mark_rollback()

        # Capture a new snapshot recording the rollback
        self.snapshot(
            record,
            bump=VersionBump.SNAPSHOT,
            change_summary=f"Rollback to snapshot {snapshot_id}",
            created_by=rolled_back_by,
        )

        _LOG.info("Rolled back '%s' to snapshot '%s'", record.id, snapshot_id)
        return record

    # ── Diff ─────────────────────────────────────────────────────────────────

    def diff(self, snap_before: KnowledgeSnapshot, snap_after: KnowledgeSnapshot) -> VersionDiff:
        """Return a VersionDiff summarising changes between two snapshots."""
        fields_changed = []
        a = snap_before.payload
        b = snap_after.payload
        for key in set(list(a.keys()) + list(b.keys())):
            if a.get(key) != b.get(key):
                fields_changed.append(key)
        return VersionDiff(
            snapshot_id_before = snap_before.snapshot_id,
            snapshot_id_after  = snap_after.snapshot_id,
            fields_changed     = fields_changed,
            summary            = f"{len(fields_changed)} field(s) changed",
        )

    def clear_history(self, knowledge_id: str) -> int:
        with self._lock:
            n = len(self._history.get(knowledge_id, []))
            self._history.pop(knowledge_id, None)
            return n

    def reset(self) -> None:
        with self._lock:
            self._history.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_versioning_engine() -> KnowledgeVersioningEngine:
    global _engine
    with _lock:
        if _engine is None:
            _engine = KnowledgeVersioningEngine()
        return _engine


def reset_versioning_engine() -> None:
    global _engine
    with _lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
