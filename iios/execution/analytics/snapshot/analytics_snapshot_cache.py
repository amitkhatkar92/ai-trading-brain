"""
iios/execution/analytics/snapshot/analytics_snapshot_cache.py
=============================================================
AnalyticsSnapshotCache — fast bounded LRU cache for snapshot lookup.

Recent snapshots are kept in memory for O(1) retrieval.
When the cache is full the oldest entry is evicted.

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import collections
import threading
import time
from typing import Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .analytics_snapshot_events import make_snapshot_cached_event
from .analytics_snapshot_history import AnalyticsSnapshotHistory
from .constants import (
    ACTOR_STORE,
    CACHE_SYSTEM_ID,
    DEFAULT_CACHE_SIZE,
    DEFAULT_SNAPSHOT_TTL,
)
from .exceptions import SnapshotEngineNotRunningError
from .execution_analytics_snapshot import ExecutionAnalyticsSnapshot

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsSnapshotCache(LifecycleAwareMixin):
    """
    Bounded LRU cache for ExecutionAnalyticsSnapshot objects.

    Entries are evicted when:
      - The cache is full (oldest entry removed).
      - The entry's TTL has expired.

    Thread-safe.  Must be started before use.
    """

    def __init__(
        self,
        max_size: int   = DEFAULT_CACHE_SIZE,
        ttl_seconds: float = DEFAULT_SNAPSHOT_TTL,
    ) -> None:
        super().__init__()
        self._max_size   = max_size
        self._ttl        = ttl_seconds
        self._lock       = threading.Lock()
        # OrderedDict used as LRU: key = snapshot_id, value = (snapshot, inserted_at)
        self._cache: collections.OrderedDict[
            str, tuple[ExecutionAnalyticsSnapshot, float]
        ] = collections.OrderedDict()
        self._hits   = 0
        self._misses = 0

    def _on_start(self) -> None:
        _log.info("AnalyticsSnapshotCache started.", system_id=CACHE_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("AnalyticsSnapshotCache stopped.", system_id=CACHE_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def put(self, snapshot: ExecutionAnalyticsSnapshot) -> None:
        """Insert or update a snapshot in the cache."""
        self._assert_running()
        with self._lock:
            sid = snapshot.snapshot_id
            if sid in self._cache:
                self._cache.move_to_end(sid)
                self._cache[sid] = (snapshot, time.time())
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)  # evict oldest
                self._cache[sid] = (snapshot, time.time())

    def get(self, snapshot_id: str) -> Optional[ExecutionAnalyticsSnapshot]:
        """
        Retrieve a snapshot by ID.

        Returns None if not cached or TTL expired.
        """
        self._assert_running()
        with self._lock:
            entry = self._cache.get(snapshot_id)
            if entry is None:
                self._misses += 1
                return None
            snap, inserted = entry
            if time.time() - inserted > self._ttl:
                del self._cache[snapshot_id]
                self._misses += 1
                return None
            self._cache.move_to_end(snapshot_id)
            self._hits += 1
            return snap

    def evict(self, snapshot_id: str) -> None:
        """Explicitly remove an entry from the cache."""
        with self._lock:
            self._cache.pop(snapshot_id, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits   = 0
            self._misses = 0

    def purge_expired(self) -> int:
        """Evict all entries whose TTL has expired. Returns the number removed."""
        now = time.time()
        removed = 0
        with self._lock:
            expired = [
                k for k, (_, inserted) in self._cache.items()
                if now - inserted > self._ttl
            ]
            for k in expired:
                del self._cache[k]
                removed += 1
        return removed

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    @property
    def hit_count(self) -> int:
        with self._lock:
            return self._hits

    @property
    def miss_count(self) -> int:
        with self._lock:
            return self._misses

    @property
    def hit_rate(self) -> float:
        with self._lock:
            total = self._hits + self._misses
            return self._hits / total if total else 0.0

    @property
    def max_size(self) -> int:
        return self._max_size
