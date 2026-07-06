"""
iios/infrastructure/cache/cache_manager.py
==========================================
Manages multiple named caches and provides a unified interface.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from ..infrastructure_constants import (
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL_SECONDS,
    CachePolicy as CachePolicyEnum,
)
from ..infrastructure_exceptions import CacheError
from ..infrastructure_models import CacheStats
from .memory_cache import MemoryCache

__all__ = ["CacheManager", "get_cache_manager", "reset_cache_manager"]

_mgr_lock = threading.Lock()
_manager: Optional["CacheManager"] = None


class CacheManager:
    """Registry of named ``MemoryCache`` instances.

    Usage::

        mgr = get_cache_manager()
        mgr.create("quotes", max_size=5000, ttl=30)
        cache = mgr.get("quotes")
        cache.set("RELIANCE", quote_obj)
    """

    def __init__(self) -> None:
        self._caches: dict[str, MemoryCache] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        max_size: int = DEFAULT_CACHE_MAX_SIZE,
        ttl: float = DEFAULT_CACHE_TTL_SECONDS,
        policy: CachePolicyEnum = CachePolicyEnum.LRU,
        allow_override: bool = False,
    ) -> MemoryCache:
        """Create a named cache.

        Args:
            name:           Unique cache name.
            max_size:       Maximum number of entries.
            ttl:            Default TTL in seconds (0 = no expiry).
            policy:         Eviction policy (LRU/LFU/FIFO).
            allow_override: If True, replaces an existing cache with the same name.
        """
        with self._lock:
            if name in self._caches and not allow_override:
                raise CacheError(
                    f"Cache '{name}' already exists",
                    code="INF-CACHE-001",
                    context={"name": name},
                )
            cache: MemoryCache = MemoryCache(
                max_size=max_size,
                default_ttl=ttl,
                policy=policy,
                name=name,
            )
            self._caches[name] = cache
            return cache

    def get(self, name: str) -> MemoryCache:
        """Return a named cache; raises ``CacheError`` if not found."""
        with self._lock:
            c = self._caches.get(name)
        if c is None:
            raise CacheError(
                f"Cache '{name}' not found",
                code="INF-CACHE-002",
                context={"name": name},
            )
        return c

    def get_or_create(
        self,
        name: str,
        max_size: int = DEFAULT_CACHE_MAX_SIZE,
        ttl: float = DEFAULT_CACHE_TTL_SECONDS,
        policy: CachePolicyEnum = CachePolicyEnum.LRU,
    ) -> MemoryCache:
        """Return existing cache or create it on demand."""
        with self._lock:
            if name not in self._caches:
                self._caches[name] = MemoryCache(
                    max_size=max_size,
                    default_ttl=ttl,
                    policy=policy,
                    name=name,
                )
            return self._caches[name]

    def remove(self, name: str) -> bool:
        with self._lock:
            return self._caches.pop(name, None) is not None

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._caches

    def names(self) -> list[str]:
        with self._lock:
            return list(self._caches.keys())

    # ------------------------------------------------------------------
    # Aggregated operations
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        with self._lock:
            for cache in self._caches.values():
                cache.clear()

    def purge_expired_all(self) -> dict[str, int]:
        """Purge expired entries from all caches. Returns per-cache counts."""
        with self._lock:
            caches = dict(self._caches)
        return {name: c.purge_expired() for name, c in caches.items()}

    def all_stats(self) -> dict[str, CacheStats]:
        with self._lock:
            caches = dict(self._caches)
        return {name: c.stats() for name, c in caches.items()}

    def total_entries(self) -> int:
        with self._lock:
            return sum(c.size() for c in self._caches.values())

    def reset(self) -> None:
        with self._lock:
            self._caches.clear()


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


def get_cache_manager() -> CacheManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = CacheManager()
        return _manager


def reset_cache_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
