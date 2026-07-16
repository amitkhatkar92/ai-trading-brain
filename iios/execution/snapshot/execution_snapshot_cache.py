"""iios/execution/snapshot/execution_snapshot_cache.py
==================================================
ExecutionSnapshotCache — bounded in-memory LRU cache for fast
lookup of recently accessed ExecutionSnapshot objects.

Wraps ExecutionSnapshotStore for write-through caching.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import CACHE_SYSTEM_ID, DEFAULT_CACHE_SIZE
from .execution_snapshot import ExecutionSnapshot

_log = get_logger(__name__, engine_id=CACHE_SYSTEM_ID)


class ExecutionSnapshotCache:
    """
    Bounded LRU in-memory cache for ExecutionSnapshot objects.

    Thread-safe. Evicts least-recently-used entries when at capacity.
    """

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        self._max_size   = max_size
        self._cache:     OrderedDict[str, ExecutionSnapshot] = OrderedDict()
        self._lock       = threading.Lock()

        # Metrics
        self._hits:   int = 0
        self._misses: int = 0
        self._evictions: int = 0

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[ExecutionSnapshot]:
        """
        Return a snapshot from cache, or None on miss.
        Moves the entry to the end (most-recently-used) on hit.
        """
        with self._lock:
            snap = self._cache.get(snapshot_id)
            if snap is None:
                self._misses += 1
                return None
            # Promote to MRU
            self._cache.move_to_end(snapshot_id)
            self._hits += 1
            return snap

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._cache

    # ── Write ─────────────────────────────────────────────────────────────────

    def put(self, snapshot: ExecutionSnapshot) -> None:
        """Insert or update a snapshot. Evicts LRU if at capacity."""
        with self._lock:
            if snapshot.snapshot_id in self._cache:
                self._cache.move_to_end(snapshot.snapshot_id)
                self._cache[snapshot.snapshot_id] = snapshot
                return
            if len(self._cache) >= self._max_size:
                evicted_id, _ = self._cache.popitem(last=False)
                self._evictions += 1
                _log.debug("Cache eviction.", evicted_snapshot_id=evicted_id)
            self._cache[snapshot.snapshot_id] = snapshot

    def invalidate(self, snapshot_id: str) -> bool:
        """Remove a snapshot from cache. Returns True if it was present."""
        with self._lock:
            if snapshot_id in self._cache:
                del self._cache[snapshot_id]
                return True
        return False

    def clear(self) -> None:
        """Evict all entries."""
        with self._lock:
            self._cache.clear()

    # ── Queries ───────────────────────────────────────────────────────────────

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def peek_ids(self) -> list[str]:
        """Return all cached snapshot IDs (LRU → MRU order)."""
        with self._lock:
            return list(self._cache.keys())

    # ── Metrics ───────────────────────────────────────────────────────────────

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            size = len(self._cache)
        return {
            "max_size":   self._max_size,
            "size":       size,
            "hits":       self._hits,
            "misses":     self._misses,
            "evictions":  self._evictions,
            "hit_rate":   round(self.hit_rate, 4),
            "utilisation": round(size / self._max_size, 4) if self._max_size else 0.0,
        }
