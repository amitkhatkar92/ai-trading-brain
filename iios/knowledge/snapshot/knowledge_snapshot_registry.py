"""
knowledge_snapshot_registry.py — iios.knowledge.snapshot
----------------------------------------------------------
Thread-safe registry of active KnowledgeSnapshot instances.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_SNAPSHOTS
from .exceptions import SnapshotCapacityError, SnapshotNotFoundError
from .knowledge_snapshot import KnowledgeSnapshot

_log = get_logger(__name__)


class KnowledgeSnapshotRegistry:
    """
    Thread-safe in-memory registry of KnowledgeSnapshot objects.

    Keyed by snapshot_id.
    Raises SnapshotCapacityError if max_snapshots is exceeded.
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._max_snapshots = max_snapshots
        self._store: Dict[str, KnowledgeSnapshot] = {}
        self._lock  = threading.Lock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register(self, snapshot: KnowledgeSnapshot) -> None:
        with self._lock:
            if (
                len(self._store) >= self._max_snapshots
                and snapshot.snapshot_id not in self._store
            ):
                raise SnapshotCapacityError(limit=self._max_snapshots)
            self._store[snapshot.snapshot_id] = snapshot
        _log.debug(f"Snapshot registered: id={snapshot.snapshot_id!r}")

    def remove(self, snapshot_id: str) -> bool:
        with self._lock:
            if snapshot_id in self._store:
                del self._store[snapshot_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[KnowledgeSnapshot]:
        with self._lock:
            return self._store.get(snapshot_id)

    def get_or_raise(self, snapshot_id: str) -> KnowledgeSnapshot:
        snap = self.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def by_session(self, knowledge_session_id: str) -> List[KnowledgeSnapshot]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.knowledge_session_id == knowledge_session_id
            ]

    def all_snapshot_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def all_snapshots(self) -> List[KnowledgeSnapshot]:
        with self._lock:
            return list(self._store.values())

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._store

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
