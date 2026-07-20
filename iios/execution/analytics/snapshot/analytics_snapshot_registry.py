"""
iios/execution/analytics/snapshot/analytics_snapshot_registry.py
================================================================
AnalyticsSnapshotRegistry — tracks active snapshots and prevents
duplicate snapshot IDs.

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DEFAULT_MAX_SNAPSHOTS, REGISTRY_SYSTEM_ID
from .exceptions import (
    SnapshotDuplicateError,
    SnapshotEngineNotRunningError,
    SnapshotNotFoundError,
)
from .execution_analytics_snapshot import ExecutionAnalyticsSnapshot

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsSnapshotRegistry(LifecycleAwareMixin):
    """
    Active snapshot registry.

    Guarantees uniqueness of snapshot IDs within the active set.
    When max_size is reached the oldest entry is evicted automatically.

    Thread-safe.  Must be started before use.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        super().__init__()
        self._max_size = max_size
        self._lock     = threading.Lock()
        self._active:  Dict[str, ExecutionAnalyticsSnapshot] = {}
        self._ordered: List[str] = []   # insertion order for eviction

    def _on_start(self) -> None:
        _log.info("AnalyticsSnapshotRegistry started.", system_id=REGISTRY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("AnalyticsSnapshotRegistry stopped.", system_id=REGISTRY_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def register(self, snapshot: ExecutionAnalyticsSnapshot) -> None:
        """
        Register a snapshot as active.

        Raises SnapshotDuplicateError if the snapshot_id is already
        present.  Evicts the oldest entry if at capacity.
        """
        self._assert_running()
        with self._lock:
            sid = snapshot.snapshot_id
            if sid in self._active:
                raise SnapshotDuplicateError(sid)
            if len(self._active) >= self._max_size:
                oldest = self._ordered.pop(0)
                del self._active[oldest]
            self._active[sid] = snapshot
            self._ordered.append(sid)

    def get(self, snapshot_id: str) -> ExecutionAnalyticsSnapshot:
        """Return an active snapshot by ID or raise SnapshotNotFoundError."""
        with self._lock:
            snap = self._active.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._active

    def remove(self, snapshot_id: str) -> None:
        """Remove a snapshot from the active registry (no error if absent)."""
        with self._lock:
            if snapshot_id in self._active:
                del self._active[snapshot_id]
                try:
                    self._ordered.remove(snapshot_id)
                except ValueError:
                    pass

    def list_all(self) -> List[ExecutionAnalyticsSnapshot]:
        with self._lock:
            return list(self._active.values())

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._active)

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._ordered.clear()
