"""
knowledge_snapshot_cache.py — iios.knowledge.snapshot
-------------------------------------------------------
LRU (least-recently-used) cache for KnowledgeSnapshot objects.

Frequently accessed snapshots stay in cache; the oldest are evicted
when the cache is full.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_CACHE_SIZE
from .knowledge_snapshot import KnowledgeSnapshot

_log = get_logger(__name__)


class KnowledgeSnapshotCache:
    """
    Thread-safe LRU cache of KnowledgeSnapshot objects.

    On get() the accessed snapshot moves to the most-recently-used position.
    When the cache is full, the least-recently-used snapshot is evicted.
    """

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        self._max_size  = max(1, max_size)
        self._cache: OrderedDict[str, KnowledgeSnapshot] = OrderedDict()
        self._hits    = 0
        self._misses  = 0
        self._evicted = 0
        self._lock    = threading.Lock()

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[KnowledgeSnapshot]:
        """Return cached snapshot and promote to MRU position."""
        with self._lock:
            if snapshot_id in self._cache:
                self._cache.move_to_end(snapshot_id)
                self._hits += 1
                return self._cache[snapshot_id]
            self._misses += 1
            return None

    def put(self, snapshot: KnowledgeSnapshot) -> None:
        """Insert snapshot into cache; evict LRU entry if full."""
        with self._lock:
            if snapshot.snapshot_id in self._cache:
                self._cache.move_to_end(snapshot.snapshot_id)
                self._cache[snapshot.snapshot_id] = snapshot
                return
            if len(self._cache) >= self._max_size:
                evicted_id, _ = self._cache.popitem(last=False)   # pop LRU
                self._evicted += 1
                _log.debug(f"Cache evicted: id={evicted_id!r}")
            self._cache[snapshot.snapshot_id] = snapshot

    def invalidate(self, snapshot_id: str) -> bool:
        with self._lock:
            if snapshot_id in self._cache:
                del self._cache[snapshot_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def hits(self) -> int:
        with self._lock:
            return self._hits

    def misses(self) -> int:
        with self._lock:
            return self._misses

    def evictions(self) -> int:
        with self._lock:
            return self._evicted

    def hit_rate(self) -> float:
        with self._lock:
            total = self._hits + self._misses
            return self._hits / total if total > 0 else 0.0

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits    = 0
            self._misses  = 0
            self._evicted = 0
