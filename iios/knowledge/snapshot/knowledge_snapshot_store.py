"""
knowledge_snapshot_store.py — iios.knowledge.snapshot
-------------------------------------------------------
Persistent-ready snapshot store backed by an in-memory dict.

Supports get, put, delete, list operations.
Snapshots can be serialized to/from JSON for external persistence.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Iterator, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_SNAPSHOTS
from .exceptions import SnapshotCapacityError, SnapshotNotFoundError, SnapshotStoreError
from .knowledge_snapshot import KnowledgeSnapshot

_log = get_logger(__name__)


class KnowledgeSnapshotStore:
    """
    Thread-safe in-memory snapshot store.

    Primary persistence layer for KnowledgeSnapshot objects.
    All snapshots are immutable once stored.
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._max  = max_snapshots
        self._data: Dict[str, KnowledgeSnapshot] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def put(self, snapshot: KnowledgeSnapshot) -> None:
        """Store a snapshot.  Overwrites if snapshot_id already exists."""
        with self._lock:
            if (
                len(self._data) >= self._max
                and snapshot.snapshot_id not in self._data
            ):
                raise SnapshotCapacityError(limit=self._max)
            self._data[snapshot.snapshot_id] = snapshot
        _log.debug(f"Snapshot stored: id={snapshot.snapshot_id!r}")

    def delete(self, snapshot_id: str) -> bool:
        with self._lock:
            if snapshot_id in self._data:
                del self._data[snapshot_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[KnowledgeSnapshot]:
        with self._lock:
            return self._data.get(snapshot_id)

    def get_or_raise(self, snapshot_id: str) -> KnowledgeSnapshot:
        snap = self.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def list_ids(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    def list_snapshots(self) -> List[KnowledgeSnapshot]:
        with self._lock:
            return list(self._data.values())

    def by_session(self, knowledge_session_id: str) -> List[KnowledgeSnapshot]:
        with self._lock:
            return [
                s for s in self._data.values()
                if s.knowledge_session_id == knowledge_session_id
            ]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._data)

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._data

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def export_all(self) -> List[Dict[str, Any]]:
        """Export all snapshots as a list of serializable dicts."""
        with self._lock:
            snapshots = list(self._data.values())
        return [s.to_dict() for s in snapshots]

    def import_all(
        self, records: List[Dict[str, Any]], *, overwrite: bool = True,
    ) -> int:
        """Import snapshots from serializable dicts.  Returns count imported."""
        imported = 0
        for record in records:
            try:
                snap = KnowledgeSnapshot.from_dict(record)
                if not overwrite and self.contains(snap.snapshot_id):
                    continue
                self.put(snap)
                imported += 1
            except Exception as exc:
                _log.warning(f"Import skipped record: {exc!r}")
        return imported
