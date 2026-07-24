"""
supervisor_snapshot_registry.py — iios.supervisor.snapshot
------------------------------------------------------------
Thread-safe registry for SupervisorSnapshot instances.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SNAPSHOTS, SnapshotStatus
from .exceptions import (
    SupervisorSnapshotCapacityError,
    SupervisorSnapshotNotFoundError,
    SupervisorSnapshotRegistryError,
)
from .supervisor_snapshot import SupervisorSnapshot


class SupervisorSnapshotRegistry:
    """
    Thread-safe registry of SupervisorSnapshot instances.

    Allows retrieval by snapshot_id or supervisor_session_id.
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._lock:       threading.RLock                      = threading.RLock()
        self._max:        int                                   = max_snapshots
        self._by_id:      Dict[str, SupervisorSnapshot]        = {}
        self._by_session: Dict[str, List[str]]                 = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, snapshot: SupervisorSnapshot) -> None:
        """Register a snapshot; raises on None or at-capacity."""
        if snapshot is None:
            raise SupervisorSnapshotRegistryError("Cannot register None snapshot")
        with self._lock:
            if snapshot.snapshot_id not in self._by_id and len(self._by_id) >= self._max:
                raise SupervisorSnapshotCapacityError(self._max)
            self._by_id[snapshot.snapshot_id] = snapshot
            self._by_session.setdefault(
                snapshot.supervisor_session_id, []
            ).append(snapshot.snapshot_id)

    def unregister(self, snapshot_id: str) -> None:
        """Remove a snapshot by ID."""
        with self._lock:
            if snapshot_id not in self._by_id:
                raise SupervisorSnapshotRegistryError(
                    f"snapshot_id not found: {snapshot_id!r}"
                )
            snap = self._by_id.pop(snapshot_id)
            ids  = self._by_session.get(snap.supervisor_session_id, [])
            if snapshot_id in ids:
                ids.remove(snapshot_id)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> SupervisorSnapshot:
        """Return snapshot; raise SupervisorSnapshotNotFoundError if absent."""
        with self._lock:
            if snapshot_id not in self._by_id:
                raise SupervisorSnapshotNotFoundError(snapshot_id)
            return self._by_id[snapshot_id]

    def get_optional(self, snapshot_id: str) -> Optional[SupervisorSnapshot]:
        """Return snapshot or None."""
        with self._lock:
            return self._by_id.get(snapshot_id)

    def get_for_session(self, session_id: str) -> List[SupervisorSnapshot]:
        """Return all snapshots for a supervisor session."""
        with self._lock:
            ids = self._by_session.get(session_id, [])
            return [self._by_id[i] for i in ids if i in self._by_id]

    def latest_for_session(self, session_id: str) -> Optional[SupervisorSnapshot]:
        """Return the snapshot with the highest snapshot_timestamp for a session."""
        snaps = self.get_for_session(session_id)
        if not snaps:
            return None
        return max(snaps, key=lambda s: s.snapshot_timestamp)

    def all_snapshots(self) -> List[SupervisorSnapshot]:
        """Return all registered snapshots."""
        with self._lock:
            return list(self._by_id.values())

    def published_snapshots(self) -> List[SupervisorSnapshot]:
        """Return only published snapshots."""
        with self._lock:
            return [
                s for s in self._by_id.values()
                if s.snapshot_status == SnapshotStatus.PUBLISHED
            ]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    @property
    def published_count(self) -> int:
        return len(self.published_snapshots())

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_session.clear()
