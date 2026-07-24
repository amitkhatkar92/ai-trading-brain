"""
integration_snapshot_cache.py — iios.integration.snapshot
-----------------------------------------------------------
IntegrationSnapshotCache — thread-safe TTL cache for IntegrationSnapshot
objects with LRU eviction.

Cache entries expire after their configured TTL (default 5 minutes).
When the cache is full, the least-recently-used entry is evicted.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_CACHE_SIZE, DEFAULT_CACHE_TTL_SECONDS
from .integration_snapshot import IntegrationSnapshot

_log = get_logger(__name__)


@dataclass
class _CacheEntry:
    """Internal mutable entry in the TTL cache."""
    snapshot:     IntegrationSnapshot
    cached_at:    float     # monotonic time of insertion
    ttl_seconds:  float     # expiry window
    access_count: int = 0

    def is_expired(self) -> bool:
        return (time.monotonic() - self.cached_at) > self.ttl_seconds


@dataclass(frozen=True)
class CacheStats:
    """Immutable snapshot of cache metrics."""
    hits:       int
    misses:     int
    evictions:  int
    size:       int
    hit_rate:   float       # 0.0 – 1.0


class IntegrationSnapshotCache:
    """
    Thread-safe TTL cache with LRU eviction.

    Operations
    ----------
    put(snapshot, ttl_seconds=None) → bool
    get(snapshot_id)                → Optional[IntegrationSnapshot]
    invalidate(snapshot_id)         → bool
    clear()                         → int  (count cleared)
    stats                           → CacheStats
    size                            → int
    """

    def __init__(
        self,
        max_size:    int   = DEFAULT_CACHE_SIZE,
        ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self._max_size:   int                            = max_size
        self._default_ttl: float                         = ttl_seconds
        self._cache:      OrderedDict[str, _CacheEntry] = OrderedDict()
        self._hits:       int                            = 0
        self._misses:     int                            = 0
        self._evictions:  int                            = 0
        self._lock:       threading.Lock                 = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────

    def put(
        self,
        snapshot:    IntegrationSnapshot,
        ttl_seconds: Optional[float] = None,
    ) -> bool:
        """
        Insert or refresh a cache entry.

        If the cache is full, the least-recently-used entry is evicted.
        Returns True on success.
        """
        sid = snapshot.snapshot_id
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        with self._lock:
            if sid in self._cache:
                # Refresh existing entry (move to end = most-recently-used)
                self._cache.move_to_end(sid)
                entry = self._cache[sid]
                entry.cached_at    = time.monotonic()
                entry.ttl_seconds  = ttl
                entry.access_count = 0
                return True
            # Evict LRU if at capacity
            while len(self._cache) >= self._max_size:
                evicted_id, _ = self._cache.popitem(last=False)
                self._evictions += 1
                _log.debug(f"Cache LRU eviction: {evicted_id!r}")
            self._cache[sid] = _CacheEntry(
                snapshot    = snapshot,
                cached_at   = time.monotonic(),
                ttl_seconds = ttl,
            )
        return True

    # ── Read ──────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[IntegrationSnapshot]:
        """
        Retrieve a snapshot.

        Returns None on miss or if the entry has expired (entry is then
        evicted).  Moves valid hits to end of LRU order.
        """
        with self._lock:
            entry = self._cache.get(snapshot_id)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._cache[snapshot_id]
                self._evictions += 1
                self._misses    += 1
                _log.debug(f"Cache TTL expiry: {snapshot_id!r}")
                return None
            # Hit — move to end (most-recently-used)
            self._cache.move_to_end(snapshot_id)
            entry.access_count += 1
            self._hits         += 1
        return entry.snapshot

    def peek(self, snapshot_id: str) -> Optional[IntegrationSnapshot]:
        """Like get() but does not update LRU order or hit/miss counters."""
        with self._lock:
            entry = self._cache.get(snapshot_id)
            if entry is None or entry.is_expired():
                return None
            return entry.snapshot

    # ── Invalidation ──────────────────────────────────────────────────

    def invalidate(self, snapshot_id: str) -> bool:
        """Remove a single entry. Returns True if it existed."""
        with self._lock:
            if snapshot_id in self._cache:
                del self._cache[snapshot_id]
                self._evictions += 1
                return True
        return False

    def clear(self) -> int:
        """Remove all entries. Returns the count removed."""
        with self._lock:
            n = len(self._cache)
            self._cache.clear()
            self._evictions += n
        return n

    # ── Properties / metrics ──────────────────────────────────────────

    @property
    def size(self) -> int:
        """Number of (non-expired) entries currently in cache."""
        with self._lock:
            return len(self._cache)

    @property
    def stats(self) -> CacheStats:
        with self._lock:
            total    = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return CacheStats(
                hits      = self._hits,
                misses    = self._misses,
                evictions = self._evictions,
                size      = len(self._cache),
                hit_rate  = round(hit_rate, 4),
            )

    @property
    def max_size(self) -> int:
        return self._max_size
