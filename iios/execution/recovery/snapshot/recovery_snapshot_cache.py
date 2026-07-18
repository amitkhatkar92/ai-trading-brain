"""
iios/execution/recovery/snapshot/recovery_snapshot_cache.py
===========================================================
RecoverySnapshotCache — lifecycle-aware fast-lookup cache for the
latest ExecutionRecoverySnapshot per recovery session.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, Optional, TYPE_CHECKING

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import CACHE_ID, DEFAULT_CACHE_SIZE, VERSION
from .exceptions import SnapshotNotRunningError

if TYPE_CHECKING:
    from .execution_recovery_snapshot import ExecutionRecoverySnapshot

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class RecoverySnapshotCache(LifecycleAwareMixin):
    """
    Lifecycle-aware, bounded LRU-like cache of the latest snapshot per
    recovery_session_id.

    Tracks hit/miss counts for observability.
    """

    VERSION   = VERSION
    SYSTEM_ID = CACHE_ID

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        super().__init__()
        self._max_size  = max_size
        self._lock:     threading.Lock = threading.Lock()
        self._store:    Dict[str, "ExecutionRecoverySnapshot"] = {}
        self._hits:     int = 0
        self._misses:   int = 0

    def _on_start(self) -> None:
        _log.info("RecoverySnapshotCache started", system_id=CACHE_ID)

    def _on_stop(self) -> None:
        _log.info("RecoverySnapshotCache stopped", system_id=CACHE_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotNotRunningError()

    # ── Cache operations ──────────────────────────────────────────────────────

    def put(self, snapshot: "ExecutionRecoverySnapshot") -> None:
        """Cache the snapshot keyed by recovery_session_id (replaces existing)."""
        self._assert_running()
        with self._lock:
            # Evict oldest entry if at capacity and session not already present
            if len(self._store) >= self._max_size and \
                    snapshot.recovery_session_id not in self._store:
                # Remove the first (oldest) entry
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
            self._store[snapshot.recovery_session_id] = snapshot

    def get(self, recovery_session_id: str) -> Optional["ExecutionRecoverySnapshot"]:
        """Return the cached snapshot for the session, or None if not present."""
        self._assert_running()
        with self._lock:
            snapshot = self._store.get(recovery_session_id)
            if snapshot is None:
                self._misses += 1
            else:
                self._hits += 1
            return snapshot

    def invalidate(self, recovery_session_id: str) -> None:
        """Remove the cached snapshot for the session (no-op if not present)."""
        self._assert_running()
        with self._lock:
            self._store.pop(recovery_session_id, None)

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def cache_size(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def hit_count(self) -> int:
        with self._lock:
            return self._hits

    @property
    def miss_count(self) -> int:
        with self._lock:
            return self._misses

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits   = 0
            self._misses = 0
