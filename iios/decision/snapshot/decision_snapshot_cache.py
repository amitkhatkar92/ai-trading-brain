"""
decision_snapshot_cache.py — iios.decision.snapshot
====================================================
Thread-safe LRU cache for DecisionSnapshot objects.

Provides fast O(1) lookup by snapshot_id with automatic eviction of
the least-recently-used entry when the cache is full.

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import List, Optional

from .constants import DEFAULT_CACHE_SIZE
from .decision_snapshot import DecisionSnapshot


class DecisionSnapshotCache:
    """
    Thread-safe LRU cache for :class:`DecisionSnapshot` objects.

    Parameters
    ----------
    max_size : Maximum number of snapshots to keep in cache.
    """

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        self._lock     = threading.RLock()
        self._cache: OrderedDict[str, DecisionSnapshot] = OrderedDict()
        self._max_size = max(1, max_size)
        self._hits     = 0
        self._misses   = 0

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def put(self, snapshot: DecisionSnapshot) -> None:
        """
        Insert or update *snapshot* in the cache.
        Evicts the least-recently-used entry if the cache is full.
        """
        with self._lock:
            sid = snapshot.snapshot_id
            if sid in self._cache:
                self._cache.move_to_end(sid)
                self._cache[sid] = snapshot
            else:
                self._cache[sid] = snapshot
                if len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)

    def invalidate(self, snapshot_id: str) -> bool:
        """Remove *snapshot_id* from the cache.  Returns True if it was present."""
        with self._lock:
            if snapshot_id in self._cache:
                del self._cache[snapshot_id]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        """Return the snapshot for *snapshot_id*, or None on miss."""
        with self._lock:
            if snapshot_id in self._cache:
                self._hits += 1
                self._cache.move_to_end(snapshot_id)
                return self._cache[snapshot_id]
            self._misses += 1
            return None

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._cache

    def all_snapshots(self) -> List[DecisionSnapshot]:
        with self._lock:
            return list(self._cache.values())

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size":        len(self._cache),
                "max_size":    self._max_size,
                "hits":        self._hits,
                "misses":      self._misses,
                "hit_rate":    self._hits / total if total else 0.0,
            }
