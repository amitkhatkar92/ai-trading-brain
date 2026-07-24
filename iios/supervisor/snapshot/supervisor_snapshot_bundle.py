"""
supervisor_snapshot_bundle.py — iios.supervisor.snapshot
---------------------------------------------------------
SupervisorSnapshotBundle — an immutable group of related snapshots.
SupervisorSnapshotBundleBuilder — mutable builder for constructing bundles.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import SupervisorSnapshotBundleError, SupervisorSnapshotNotFoundError
from .supervisor_snapshot import SupervisorSnapshot


@dataclass(frozen=True)
class SupervisorSnapshotBundle:
    """
    Immutable bundle of related SupervisorSnapshot instances.

    Use :class:`SupervisorSnapshotBundleBuilder` to construct bundles.
    """
    bundle_id:   str
    session_id:  str
    snapshots:   Tuple[SupervisorSnapshot, ...]
    created_at:  float
    description: str = ""

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        return len(self.snapshots)

    @property
    def latest(self) -> Optional[SupervisorSnapshot]:
        """Return the most recently timestamped snapshot."""
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.snapshot_timestamp)

    @property
    def oldest(self) -> Optional[SupervisorSnapshot]:
        """Return the oldest snapshot."""
        if not self.snapshots:
            return None
        return min(self.snapshots, key=lambda s: s.snapshot_timestamp)

    def get(self, snapshot_id: str) -> Optional[SupervisorSnapshot]:
        """Return a snapshot by ID or None."""
        for s in self.snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def emergency_snapshots(self) -> Tuple[SupervisorSnapshot, ...]:
        """Return only emergency-state snapshots."""
        return tuple(s for s in self.snapshots if s.is_emergency)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":    self.bundle_id,
            "session_id":   self.session_id,
            "count":        self.count,
            "created_at":   self.created_at,
            "description":  self.description,
            "snapshot_ids": [s.snapshot_id for s in self.snapshots],
        }


class SupervisorSnapshotBundleBuilder:
    """
    Mutable, thread-safe builder for SupervisorSnapshotBundle.

    Usage::

        bundle = (
            SupervisorSnapshotBundleBuilder("sess-1", description="daily")
            .add(snap_a)
            .add(snap_b)
            .build()
        )
    """

    def __init__(self, session_id: str, description: str = "") -> None:
        if not session_id:
            raise SupervisorSnapshotBundleError("session_id must not be empty")
        self._bundle_id   = str(uuid.uuid4())
        self._session_id  = session_id
        self._description = description
        self._snapshots:  Dict[str, SupervisorSnapshot] = {}
        self._lock        = threading.Lock()
        self._created_at  = time.time()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, snapshot: SupervisorSnapshot) -> "SupervisorSnapshotBundleBuilder":
        """Add a snapshot to the bundle."""
        if snapshot is None:
            raise SupervisorSnapshotBundleError("Cannot add None snapshot")
        with self._lock:
            self._snapshots[snapshot.snapshot_id] = snapshot
        return self

    def remove(self, snapshot_id: str) -> "SupervisorSnapshotBundleBuilder":
        """Remove a snapshot from the bundle."""
        with self._lock:
            if snapshot_id not in self._snapshots:
                raise SupervisorSnapshotNotFoundError(snapshot_id)
            del self._snapshots[snapshot_id]
        return self

    def build(self) -> SupervisorSnapshotBundle:
        """Build and return the immutable bundle."""
        with self._lock:
            snaps = tuple(self._snapshots.values())
        return SupervisorSnapshotBundle(
            bundle_id   = self._bundle_id,
            session_id  = self._session_id,
            snapshots   = snaps,
            created_at  = self._created_at,
            description = self._description,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)
