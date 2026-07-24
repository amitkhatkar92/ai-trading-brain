"""
supervisor_snapshot_store.py — iios.supervisor.snapshot
---------------------------------------------------------
Persistent store for SupervisorSnapshot instances.

Current implementation: in-memory.
Designed to be extended to SQLite / Redis without interface changes.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SNAPSHOTS
from .exceptions import (
    SupervisorSnapshotCapacityError,
    SupervisorSnapshotNotFoundError,
    SupervisorSnapshotStoreError,
)
from .supervisor_snapshot import SupervisorSnapshot


class SupervisorSnapshotStore:
    """Thread-safe persistent store for SupervisorSnapshot instances."""

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._lock:  threading.Lock                  = threading.Lock()
        self._max:   int                             = max_snapshots
        self._store: Dict[str, SupervisorSnapshot]   = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, snapshot: SupervisorSnapshot) -> None:
        """Persist a snapshot."""
        if snapshot is None:
            raise SupervisorSnapshotStoreError("Cannot save None snapshot")
        with self._lock:
            if snapshot.snapshot_id not in self._store and len(self._store) >= self._max:
                raise SupervisorSnapshotCapacityError(self._max)
            self._store[snapshot.snapshot_id] = snapshot

    def delete(self, snapshot_id: str) -> None:
        """Remove a snapshot from the store."""
        with self._lock:
            if snapshot_id not in self._store:
                raise SupervisorSnapshotNotFoundError(snapshot_id)
            del self._store[snapshot_id]

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load(self, snapshot_id: str) -> Optional[SupervisorSnapshot]:
        """Return a snapshot by ID or None if absent."""
        with self._lock:
            return self._store.get(snapshot_id)

    def load_or_raise(self, snapshot_id: str) -> SupervisorSnapshot:
        """Return a snapshot by ID; raise if not found."""
        with self._lock:
            if snapshot_id not in self._store:
                raise SupervisorSnapshotNotFoundError(snapshot_id)
            return self._store[snapshot_id]

    def list_snapshot_ids(self) -> List[str]:
        """Return all stored snapshot IDs."""
        with self._lock:
            return list(self._store.keys())

    def all_snapshots(self) -> List[SupervisorSnapshot]:
        """Return all stored snapshots."""
        with self._lock:
            return list(self._store.values())

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
