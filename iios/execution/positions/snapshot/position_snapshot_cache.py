"""iios/execution/positions/snapshot/position_snapshot_cache.py
==================================================
PositionSnapshotCache — fast in-memory latest-snapshot cache.

Provides O(1) lookup of the most recently published/valid snapshot
per position_id.  Separate from the registry so it can be invalidated
independently and maintained with different eviction semantics.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    CACHE_SYSTEM_ID,
    DEFAULT_MAX_CACHE_ENTRIES,
    VERSION,
)
from .exceptions import PositionSnapshotNotRunningError
from .position_snapshot import PositionSnapshot

_log   = get_logger(__name__, engine_id=CACHE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=CACHE_SYSTEM_ID)


class PositionSnapshotCache(LifecycleAwareMixin):
    """
    Thread-safe in-memory cache of the most-recently-stored
    ``PositionSnapshot`` per position_id.

    Write operations require RUNNING state.
    Read operations are always permitted (return ``None`` if not started).
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_CACHE_ENTRIES) -> None:
        super().__init__()
        self._max      = max(1, max_entries)
        self._cache: Dict[str, PositionSnapshot] = {}
        self._hits     = 0
        self._misses   = 0
        self._lock     = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            CACHE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("PositionSnapshotCache started.", max_entries=self._max)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            CACHE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("PositionSnapshotCache stopped.", cached_entries=self.count())

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionSnapshotNotRunningError()

    # ── Write ─────────────────────────────────────────────────────────────────

    def put(self, position_id: str, snapshot: PositionSnapshot) -> None:
        """
        Cache *snapshot* under *position_id*.

        If the cache is at capacity and *position_id* is not already
        cached, the entry is silently dropped (best-effort cache).

        Raises
        ------
        PositionSnapshotNotRunningError
        """
        self._assert_running()
        with self._lock:
            if position_id not in self._cache and len(self._cache) >= self._max:
                _log.debug("Cache full, entry dropped.", position_id=position_id)
                return
            self._cache[position_id] = snapshot

    def invalidate(self, position_id: str) -> bool:
        """
        Remove the cached snapshot for *position_id*.

        Returns ``True`` if an entry was present and removed, ``False`` otherwise.
        """
        with self._lock:
            existed = position_id in self._cache
            self._cache.pop(position_id, None)
        return existed

    def clear(self) -> int:
        """Remove all cached entries.  Returns the number of entries cleared."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits   = 0
            self._misses = 0
        return count

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, position_id: str) -> Optional[PositionSnapshot]:
        """Return the cached snapshot, or ``None`` if not cached."""
        with self._lock:
            snap = self._cache.get(position_id)
            if snap is not None:
                self._hits += 1
            else:
                self._misses += 1
        return snap

    def is_cached(self, position_id: str) -> bool:
        with self._lock:
            return position_id in self._cache

    def all_cached(self) -> List[PositionSnapshot]:
        with self._lock:
            return list(self._cache.values())

    def all_position_ids(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._cache)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._cache) == 0

    # ── Statistics ────────────────────────────────────────────────────────────

    @property
    def hits(self) -> int:
        with self._lock:
            return self._hits

    @property
    def misses(self) -> int:
        with self._lock:
            return self._misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate in [0.0, 1.0].  Returns 0.0 if no accesses yet."""
        with self._lock:
            total = self._hits + self._misses
            if total == 0:
                return 0.0
            return self._hits / total
