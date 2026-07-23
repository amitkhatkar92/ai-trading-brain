"""
risk_snapshot_cache.py — iios.risk.snapshot
=============================================
TTL-based in-memory cache for RiskSnapshot instances.

Provides fast retrieval for the most recently accessed snapshots,
with automatic expiry based on a configurable TTL.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .constants import DEFAULT_CACHE_MAX_SIZE, DEFAULT_CACHE_TTL_S
from .exceptions import RiskSnapshotCacheError, RiskSnapshotCapacityError
from .risk_snapshot import RiskSnapshot


@dataclass
class _CacheEntry:
    """Internal cache entry with TTL tracking."""
    snapshot: RiskSnapshot
    inserted_at: float
    ttl_s: float

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.inserted_at) > self.ttl_s


class RiskSnapshotCache:
    """
    Thread-safe TTL cache for :class:`~.risk_snapshot.RiskSnapshot`.

    Parameters
    ----------
    ttl_s :
        Time-to-live in seconds. Defaults to
        :data:`~.constants.DEFAULT_CACHE_TTL_S` (300 s).
    max_size :
        Maximum cache entries. Defaults to
        :data:`~.constants.DEFAULT_CACHE_MAX_SIZE` (1 000).
    """

    def __init__(
        self,
        ttl_s:    float = DEFAULT_CACHE_TTL_S,
        max_size: int   = DEFAULT_CACHE_MAX_SIZE,
    ) -> None:
        self._ttl      = ttl_s
        self._max_size = max_size
        self._lock     = threading.RLock()
        self._cache:   Dict[str, _CacheEntry] = {}
        self._hits:    int = 0
        self._misses:  int = 0
        self._evictions: int = 0

    # ------------------------------------------------------------------
    # Cache operations
    # ------------------------------------------------------------------

    def put(self, snapshot: RiskSnapshot, ttl_s: Optional[float] = None) -> None:
        """
        Insert or replace a snapshot in the cache.

        Raises
        ------
        RiskSnapshotCapacityError
            When cache is full and no expired entries can be evicted.
        """
        ttl = ttl_s if ttl_s is not None else self._ttl
        with self._lock:
            # Evict expired entries first
            self._evict_expired()
            if snapshot.snapshot_id not in self._cache:
                if len(self._cache) >= self._max_size:
                    raise RiskSnapshotCapacityError(
                        f"Snapshot cache at capacity ({self._max_size})"
                    )
            self._cache[snapshot.snapshot_id] = _CacheEntry(
                snapshot    = snapshot,
                inserted_at = time.time(),
                ttl_s       = ttl,
            )

    def get(self, snapshot_id: str) -> Optional[RiskSnapshot]:
        """
        Retrieve a snapshot. Returns None if not cached or expired.
        Updates hit/miss counters.
        """
        with self._lock:
            entry = self._cache.get(snapshot_id)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                del self._cache[snapshot_id]
                self._evictions += 1
                self._misses    += 1
                return None
            self._hits += 1
            return entry.snapshot

    def invalidate(self, snapshot_id: str) -> bool:
        """Remove a snapshot from cache. Returns True if it was cached."""
        with self._lock:
            return self._cache.pop(snapshot_id, None) is not None

    def invalidate_for_portfolio(self, portfolio_id: str) -> int:
        """Invalidate all cached snapshots for a portfolio. Returns count removed."""
        with self._lock:
            to_remove = [
                sid for sid, e in self._cache.items()
                if e.snapshot.portfolio_id == portfolio_id
            ]
            for sid in to_remove:
                del self._cache[sid]
        return len(to_remove)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_expired(self) -> int:
        """Remove all expired entries. Must be called under lock."""
        expired = [sid for sid, e in self._cache.items() if e.is_expired]
        for sid in expired:
            del self._cache[sid]
        self._evictions += len(expired)
        return len(expired)

    def evict_expired(self) -> int:
        """Public wrapper to evict expired entries."""
        with self._lock:
            return self._evict_expired()

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def hit_rate(self) -> float:
        with self._lock:
            total = self._hits + self._misses
            return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict:
        with self._lock:
            return {
                "size":      len(self._cache),
                "hits":      self._hits,
                "misses":    self._misses,
                "evictions": self._evictions,
                "hit_rate":  self.hit_rate(),
                "max_size":  self._max_size,
                "ttl_s":     self._ttl,
            }

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            entry = self._cache.get(snapshot_id)
            if entry is None:
                return False
            if entry.is_expired:
                del self._cache[snapshot_id]
                self._evictions += 1
                return False
            return True
