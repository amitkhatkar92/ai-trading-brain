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


# ---------------------------------------------------------------------------
# Multi-Level Cache Manager — production facade over CacheEngine
# ---------------------------------------------------------------------------

from typing import Any, Set  # noqa: E402  (late import to keep existing code clean)

from .cache_constants import (  # noqa: E402
    CacheLevel, CachePriority, EvictionPolicy, WritePolicy,
    DEFAULT_REGION, DEFAULT_TTL,
)
from .cache_engine import CacheEngine, SyncResult  # noqa: E402
from .cache_exceptions import CacheRegionNotFoundError  # noqa: E402
from .cache_factory import CacheFactory  # noqa: E402
from .cache_metrics import CacheMetrics  # noqa: E402
from .cache_registry import CacheRegionConfig, get_cache_registry  # noqa: E402

_ml_mgr_lock = threading.Lock()
_ml_manager: Optional["MultiLevelCacheManager"] = None


class MultiLevelCacheManager:
    """Production facade for the IIOS multi-level caching framework.

    Manages a collection of named ``CacheEngine`` instances (one per region).
    Provides the complete cache API: get, put, delete, exists, replace,
    increment, decrement, bulk ops, tag invalidation, namespace clearing,
    warm-up, and write-back sync.

    Usage::

        mgr = get_ml_cache_manager()
        mgr.put("RELIANCE:quote", quote, region="quotes", ttl=30,
                tags={"equity", "live"})
        quote = mgr.get("RELIANCE:quote", region="quotes")
        mgr.invalidate_by_tag("live", region="quotes")
    """

    def __init__(self) -> None:
        self._engines: dict[str, CacheEngine] = {}
        self._lock = threading.RLock()
        self._default_engine = CacheFactory.simple(name=DEFAULT_REGION)
        self._engines[DEFAULT_REGION] = self._default_engine

    # ── Engine management ────────────────────────────────────────────────────

    def register_region(self, config: CacheRegionConfig) -> CacheEngine:
        engine = CacheFactory.create_engine(config, shared_l2=False)
        with self._lock:
            self._engines[config.name] = engine
        return engine

    def get_engine(self, region: str = DEFAULT_REGION) -> CacheEngine:
        with self._lock:
            engine = self._engines.get(region)
        if engine is None:
            # Auto-create from registry config if available
            try:
                cfg = get_cache_registry().get(region)
                engine = CacheFactory.create_engine(cfg, shared_l2=False)
                with self._lock:
                    self._engines[region] = engine
            except CacheRegionNotFoundError:
                # Fall back to default engine
                engine = self._default_engine
        return engine

    def has_region(self, region: str) -> bool:
        with self._lock:
            return region in self._engines

    def remove_region(self, region: str) -> bool:
        with self._lock:
            engine = self._engines.pop(region, None)
            if engine:
                engine.clear_region()
            return engine is not None

    def region_names(self) -> list[str]:
        with self._lock:
            return list(self._engines.keys())

    # ── Core operations ──────────────────────────────────────────────────────

    def get(self, key: str, region: str = DEFAULT_REGION) -> Optional[Any]:
        return self.get_engine(region).get(key)

    def put(
        self,
        key: str,
        value: Any,
        *,
        region: str = DEFAULT_REGION,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None,
        priority: CachePriority = CachePriority.NORMAL,
        sliding_window: Optional[float] = None,
    ) -> bool:
        return self.get_engine(region).put(
            key, value,
            ttl=ttl,
            tags=tags or set(),
            priority=priority,
            sliding_window=sliding_window,
        )

    def delete(self, key: str, region: str = DEFAULT_REGION) -> bool:
        return self.get_engine(region).delete(key)

    def exists(self, key: str, region: str = DEFAULT_REGION) -> bool:
        return self.get_engine(region).exists(key)

    def replace(self, key: str, value: Any, region: str = DEFAULT_REGION, **kw: Any) -> bool:
        return self.get_engine(region).replace(key, value, **kw)

    def increment(
        self, key: str, delta: int = 1, default: int = 0, region: str = DEFAULT_REGION
    ) -> int:
        return self.get_engine(region).increment(key, delta=delta, default=default)

    def decrement(
        self, key: str, delta: int = 1, default: int = 0, region: str = DEFAULT_REGION
    ) -> int:
        return self.get_engine(region).decrement(key, delta=delta, default=default)

    # ── Bulk operations ──────────────────────────────────────────────────────

    def get_multi(
        self, keys: list[str], region: str = DEFAULT_REGION
    ) -> dict[str, Any]:
        return self.get_engine(region).get_multi(keys)

    def put_multi(
        self,
        mapping: dict[str, Any],
        *,
        region: str = DEFAULT_REGION,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None,
    ) -> int:
        return self.get_engine(region).put_multi(mapping, ttl=ttl, tags=tags)

    def delete_multi(self, keys: list[str], region: str = DEFAULT_REGION) -> int:
        return self.get_engine(region).delete_multi(keys)

    # ── Invalidation ─────────────────────────────────────────────────────────

    def invalidate_by_tag(self, tag: str, region: str = DEFAULT_REGION) -> int:
        return self.get_engine(region).invalidate_by_tag(tag)

    def invalidate_by_tags(self, tags: Set[str], region: str = DEFAULT_REGION) -> int:
        return self.get_engine(region).invalidate_by_tags(tags)

    # ── Namespace / region clearing ──────────────────────────────────────────

    def clear_region(self, region: str = DEFAULT_REGION) -> int:
        return self.get_engine(region).clear_region()

    def clear_namespace(self, namespace: str, region: str = DEFAULT_REGION) -> int:
        return self.get_engine(region).clear_namespace(namespace)

    def clear_all(self) -> dict[str, int]:
        with self._lock:
            engines = dict(self._engines)
        return {name: engine.clear_region() for name, engine in engines.items()}

    # ── Warm-up & Sync ───────────────────────────────────────────────────────

    def warm_up(
        self,
        data: dict[str, Any],
        *,
        region: str = DEFAULT_REGION,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None,
    ) -> int:
        return self.get_engine(region).warm_up(data, ttl=ttl, tags=tags)

    def sync(self, region: Optional[str] = None) -> dict[str, SyncResult]:
        """Flush dirty write-back entries. If *region* is None, syncs all regions."""
        with self._lock:
            targets = {region: self._engines[region]} if region else dict(self._engines)
        return {name: engine.sync() for name, engine in targets.items()}

    # ── Statistics ───────────────────────────────────────────────────────────

    def stats(self, region: str = DEFAULT_REGION) -> dict[str, Any]:
        return self.get_engine(region).stats_snapshot()

    def all_stats(self) -> dict[str, Any]:
        with self._lock:
            engines = dict(self._engines)
        return {name: eng.stats_snapshot() for name, eng in engines.items()}

    def reset(self) -> None:
        with self._lock:
            self._engines.clear()
        self._default_engine = CacheFactory.simple(name=DEFAULT_REGION)
        with self._lock:
            self._engines[DEFAULT_REGION] = self._default_engine


def get_ml_cache_manager() -> MultiLevelCacheManager:
    global _ml_manager
    with _ml_mgr_lock:
        if _ml_manager is None:
            _ml_manager = MultiLevelCacheManager()
        return _ml_manager


def reset_ml_cache_manager() -> None:
    global _ml_manager
    with _ml_mgr_lock:
        if _ml_manager is not None:
            _ml_manager.reset()
        _ml_manager = None
