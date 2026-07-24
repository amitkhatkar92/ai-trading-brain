"""
integration_snapshot_registry.py — iios.integration.snapshot
-------------------------------------------------------------
IntegrationSnapshotRegistry — thread-safe in-memory registry of
published IntegrationSnapshot objects.

Responsibilities
----------------
- Register snapshots by snapshot_id
- Retrieve by snapshot_id, session_id, or status
- Deregister snapshots
- Support status overrides without mutating the immutable snapshot

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import SnapshotStatus
from .exceptions import SnapshotNotFoundError, SnapshotRegistryError
from .integration_snapshot import IntegrationSnapshot

_log = get_logger(__name__)


class IntegrationSnapshotRegistry:
    """
    Thread-safe registry of IntegrationSnapshot objects.

    Snapshots are stored as-is (immutable).  Status overrides are
    maintained in a separate internal map so the snapshot object
    never mutates.
    """

    def __init__(self, max_size: int = 10_000) -> None:
        self._max_size:     int                            = max_size
        self._snapshots:    Dict[str, IntegrationSnapshot] = {}
        self._status_map:   Dict[str, SnapshotStatus]     = {}
        self._session_index: Dict[str, List[str]]          = {}  # session_id → [snapshot_id]
        self._lock:         threading.Lock                 = threading.Lock()

    # ── Registration ─────────────────────────────────────────────────

    def register(self, snapshot: IntegrationSnapshot) -> str:
        """
        Register a snapshot.

        Returns the snapshot_id.
        Raises SnapshotRegistryError if the registry is at capacity.
        Raises SnapshotRegistryError if snapshot_id already registered.
        """
        with self._lock:
            if len(self._snapshots) >= self._max_size:
                raise SnapshotRegistryError(
                    f"Registry at capacity ({self._max_size})"
                )
            sid = snapshot.snapshot_id
            if sid in self._snapshots:
                raise SnapshotRegistryError(
                    f"Snapshot already registered: {sid!r}"
                )
            self._snapshots[sid]    = snapshot
            self._status_map[sid]   = snapshot.status
            sess = snapshot.integration_session_id
            self._session_index.setdefault(sess, []).append(sid)
        _log.info(f"Snapshot registered: {sid!r}")
        return sid

    def deregister(self, snapshot_id: str) -> bool:
        """Remove a snapshot from the registry. Returns True if found."""
        with self._lock:
            if snapshot_id not in self._snapshots:
                return False
            snap = self._snapshots.pop(snapshot_id)
            self._status_map.pop(snapshot_id, None)
            sess = snap.integration_session_id
            ids  = self._session_index.get(sess, [])
            try:
                ids.remove(snapshot_id)
            except ValueError:
                pass
        _log.info(f"Snapshot deregistered: {snapshot_id!r}")
        return True

    # ── Status override ───────────────────────────────────────────────

    def set_status(self, snapshot_id: str, status: SnapshotStatus) -> None:
        """Override the recorded status of a snapshot."""
        with self._lock:
            if snapshot_id not in self._snapshots:
                raise SnapshotNotFoundError(snapshot_id)
            self._status_map[snapshot_id] = status
        _log.info(f"Snapshot status updated: {snapshot_id!r} → {status.value}")

    def get_status(self, snapshot_id: str) -> Optional[SnapshotStatus]:
        """Return the current (possibly overridden) status of a snapshot."""
        with self._lock:
            return self._status_map.get(snapshot_id)

    # ── Retrieval ─────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[IntegrationSnapshot]:
        """Return a snapshot by snapshot_id, or None if not found."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def get_or_raise(self, snapshot_id: str) -> IntegrationSnapshot:
        """Return a snapshot by snapshot_id; raise SnapshotNotFoundError if absent."""
        snap = self.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def get_latest(self, session_id: str) -> Optional[IntegrationSnapshot]:
        """Return the most recently registered snapshot for a session."""
        with self._lock:
            ids = self._session_index.get(session_id, [])
            if not ids:
                return None
            return self._snapshots.get(ids[-1])

    def by_session_id(self, session_id: str) -> List[IntegrationSnapshot]:
        """Return all snapshots for a given integration session."""
        with self._lock:
            ids = list(self._session_index.get(session_id, []))
        return [s for sid in ids if (s := self._snapshots.get(sid))]

    def by_status(self, status: SnapshotStatus) -> List[IntegrationSnapshot]:
        """Return all snapshots with the given current status."""
        with self._lock:
            result = [
                self._snapshots[sid]
                for sid, st in self._status_map.items()
                if st == status and sid in self._snapshots
            ]
        return result

    def list_all(self) -> List[IntegrationSnapshot]:
        """Return all registered snapshots."""
        with self._lock:
            return list(self._snapshots.values())

    def list_ids(self) -> List[str]:
        """Return all registered snapshot IDs."""
        with self._lock:
            return list(self._snapshots.keys())

    def exists(self, snapshot_id: str) -> bool:
        """Return True if snapshot_id is registered."""
        with self._lock:
            return snapshot_id in self._snapshots

    # ── Properties ───────────────────────────────────────────────────

    @property
    def count(self) -> int:
        """Number of registered snapshots."""
        with self._lock:
            return len(self._snapshots)

    @property
    def max_size(self) -> int:
        return self._max_size

    def clear(self) -> int:
        """Remove all snapshots. Returns the number removed."""
        with self._lock:
            n = len(self._snapshots)
            self._snapshots.clear()
            self._status_map.clear()
            self._session_index.clear()
        return n
