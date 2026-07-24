"""
supervisor_snapshot_cache.py — iios.supervisor.snapshot
---------------------------------------------------------
TTL-based thread-safe cache for SupervisorSnapshot instances.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple

from .constants import DEFAULT_CACHE_MAX_SIZE, DEFAULT_CACHE_TTL_S
from .supervisor_snapshot import SupervisorSnapshot


class SupervisorSnapshotCache:
    """
    Thread-safe TTL cache for SupervisorSnapshot instances.

    Entries automatically expire after their configured TTL.
    Capacity-eviction removes the entry closest to expiry when full.
    """

    def __init__(
        self,
        max_size: int   = DEFAULT_CACHE_MAX_SIZE,
        ttl_s:    float = DEFAULT_CACHE_TTL_S,
    ) -> None:
        self._lock:        threading.Lock                              = threading.Lock()
        self._max_size:    int                                         = max_size
        self._default_ttl: float                                       = ttl_s
        self._store:       Dict[str, Tuple[SupervisorSnapshot, float]] = {}
        self._hits:        int                                         = 0
        self._misses:      int                                         = 0

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def put(
        self,
        snapshot_id: str,
        snapshot:    SupervisorSnapshot,
        ttl_s:       Optional[float] = None,
    ) -> None:
        """Insert or update a cached entry."""
        expires_at = time.monotonic() + (ttl_s if ttl_s is not None else self._default_ttl)
        with self._lock:
            self._evict_expired()
            if snapshot_id not in self._store and len(self._store) >= self._max_size:
                if self._store:
                    oldest = min(self._store, key=lambda k: self._store[k][1])
                    del self._store[oldest]
            self._store[snapshot_id] = (snapshot, expires_at)

    def invalidate(self, snapshot_id: str) -> None:
        """Remove a specific entry."""
        with self._lock:
            self._store.pop(snapshot_id, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits   = 0
            self._misses = 0

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[SupervisorSnapshot]:
        """Return a snapshot or None if absent or expired."""
        with self._lock:
            entry = self._store.get(snapshot_id)
            if entry is None:
                self._misses += 1
                return None
            snapshot, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[snapshot_id]
                self._misses += 1
                return None
            self._hits += 1
            return snapshot

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
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

    @property
    def hit_rate(self) -> float:
        with self._lock:
            total = self._hits + self._misses
            return self._hits / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size":     len(self._store),
                "max_size": self._max_size,
                "hits":     self._hits,
                "misses":   self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        """Remove expired entries (must be called under lock)."""
        now     = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
