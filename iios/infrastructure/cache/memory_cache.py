"""
iios/infrastructure/cache/memory_cache.py
==========================================
In-memory cache with TTL support and pluggable eviction policies.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Generic, Hashable, Iterator, Optional, TypeVar

from ..infrastructure_constants import (
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL_SECONDS,
    CachePolicy as CachePolicyEnum,
)
from ..infrastructure_models import CacheEntry, CacheStats
from .cache_policies import CachePolicy, FIFOPolicy, LFUPolicy, LRUPolicy

__all__ = ["MemoryCache"]

V = TypeVar("V")


def _make_policy(policy: CachePolicyEnum) -> CachePolicy:
    if policy == CachePolicyEnum.LFU:
        return LFUPolicy()
    if policy == CachePolicyEnum.FIFO:
        return FIFOPolicy()
    return LRUPolicy()  # default


class MemoryCache(Generic[V]):
    """Thread-safe in-memory cache with TTL and configurable eviction.

    Usage::

        cache: MemoryCache[str] = MemoryCache(max_size=500, default_ttl=60)
        cache.set("key", "value")
        cache.set("key2", "value2", ttl=30)
        val = cache.get("key")           # returns value or None
        val = cache.get_or_set("k3", lambda: expensive_fn(), ttl=120)
    """

    def __init__(
        self,
        max_size: int = DEFAULT_CACHE_MAX_SIZE,
        default_ttl: float = DEFAULT_CACHE_TTL_SECONDS,
        policy: CachePolicyEnum = CachePolicyEnum.LRU,
        name: str = "default",
    ) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._eviction = _make_policy(policy)
        self._policy = policy
        self._name = name
        self._stats = CacheStats(max_size=max_size)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[V]:
        """Return cached value for *key*, or None if absent/expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            if entry.is_expired:
                self._delete(key)
                self._stats.misses += 1
                self._stats.expirations += 1
                return None
            entry.touch()
            self._eviction.on_access(key)
            self._stats.hits += 1
            return entry.value  # type: ignore[return-value]

    def set(
        self,
        key: str,
        value: V,
        ttl: Optional[float] = None,
        size_bytes: int = 0,
    ) -> None:
        """Store *value* under *key* with optional TTL override."""
        with self._lock:
            if key in self._store:
                self._eviction.on_delete(key)

            effective_ttl = ttl if ttl is not None else self._default_ttl
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=time.monotonic() + effective_ttl if effective_ttl > 0 else None,
                size_bytes=size_bytes,
            )
            self._store[key] = entry
            self._eviction.on_insert(key)
            self._stats.current_size = len(self._store)
            self._stats.total_bytes += size_bytes

            # Evict if over capacity
            while len(self._store) > self._max_size:
                victim = self._eviction.evict_key()
                if victim is not None and str(victim) in self._store:
                    self._delete(str(victim))
                    self._stats.evictions += 1
                else:
                    break

    def delete(self, key: str) -> bool:
        """Explicitly remove a key. Returns True if it existed."""
        with self._lock:
            return self._delete(key)

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], V],
        ttl: Optional[float] = None,
    ) -> V:
        """Return cached value or compute, cache, and return it."""
        value = self.get(key)
        if value is not None:
            return value
        computed = factory()
        self.set(key, computed, ttl=ttl)
        return computed

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                self._delete(key)
                return False
            return True

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._eviction = _make_policy(self._policy)
            self._stats.current_size = 0
            self._stats.total_bytes = 0

    def keys(self) -> list[str]:
        with self._lock:
            self._evict_expired()
            return list(self._store.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> CacheStats:
        with self._lock:
            self._stats.current_size = len(self._store)
            return self._stats

    def reset_stats(self) -> None:
        with self._lock:
            self._stats.reset()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _delete(self, key: str) -> bool:
        entry = self._store.pop(key, None)
        if entry is not None:
            self._eviction.on_delete(key)
            self._stats.current_size = len(self._store)
            return True
        return False

    def _evict_expired(self) -> int:
        expired = [k for k, e in self._store.items() if e.is_expired]
        for k in expired:
            self._delete(k)
            self._stats.expirations += 1
        return len(expired)

    def purge_expired(self) -> int:
        with self._lock:
            return self._evict_expired()

    @property
    def name(self) -> str:
        return self._name

    @property
    def max_size(self) -> int:
        return self._max_size
