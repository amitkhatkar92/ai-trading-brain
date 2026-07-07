"""
iios/infrastructure/cache/cache_engine.py
==========================================
Multi-level cache engine: coordinates L1 → L2 → L3 lookup, promotion,
write policies, tag invalidation, and bulk operations.
"""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .cache_constants import (
    CacheLevel, WritePolicy, ReadPolicy, CachePriority,
    DEFAULT_REGION, DEFAULT_TTL, EVICTION_BATCH_SIZE,
)
from .cache_entry import CacheEntry, make_entry
from .cache_exceptions import (
    CacheProviderError, CacheSyncError, CacheVersionConflictError,
)
from .cache_metrics import CacheMetrics
from .cache_provider import BaseCacheProvider, L1MemoryProvider

__all__ = ["SyncResult", "CacheEngine"]

_LOG = logging.getLogger("iios.infrastructure.cache.engine")


@dataclass
class SyncResult:
    """Outcome of a write-back flush operation."""
    flushed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failed == 0


class CacheEngine:
    """Multi-level cache engine.

    Manages up to 3 provider tiers (L1 → L2 → L3).  Implements:
    - Read-through: L1 miss → L2 → L3 → optional loader
    - Write-through: writes go to all configured levels
    - Write-back: write to L1 only; flush dirty entries on sync()
    - Write-around: skip L1/L2, write directly to L3
    - Tag-based invalidation across all levels
    - Key-prefix namespace clearing

    Usage::

        engine = CacheEngine(
            l1=L1MemoryProvider(max_size=1000),
            l2=L2SharedProvider(max_size=10000),
        )
        engine.put("RELIANCE:quote", quote_obj, ttl=30, tags={"equity", "quote"})
        quote = engine.get("RELIANCE:quote")
    """

    def __init__(
        self,
        l1: Optional[BaseCacheProvider] = None,
        l2: Optional[BaseCacheProvider] = None,
        l3: Optional[BaseCacheProvider] = None,
        write_policy: WritePolicy = WritePolicy.WRITE_THROUGH,
        read_policy: ReadPolicy = ReadPolicy.READ_ASIDE,
        loader: Optional[Callable[[str], Any]] = None,
        region: str = DEFAULT_REGION,
        default_ttl: Optional[float] = DEFAULT_TTL,
    ) -> None:
        self._l1 = l1 or L1MemoryProvider()
        self._l2 = l2
        self._l3 = l3
        self._write_policy = write_policy
        self._read_policy = read_policy
        self._loader = loader
        self._region = region
        self._default_ttl = default_ttl
        self._metrics = CacheMetrics(name=region)
        self._lock = threading.RLock()

    @property
    def region(self) -> str:
        return self._region

    @property
    def metrics(self) -> CacheMetrics:
        return self._metrics

    # ── Core read ────────────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value, or None on miss."""
        t0 = time.monotonic()
        entry, level = self._get_entry(key)
        if entry is not None:
            ms = (time.monotonic() - t0) * 1000
            self._metrics.record_hit(ms, level=level, region=self._region)
            return entry.value

        # Miss — try read-through loader
        if self._read_policy == ReadPolicy.READ_THROUGH and self._loader:
            try:
                value = self._loader(key)
                if value is not None:
                    self.put(key, value)
                    return value
            except Exception as exc:
                _LOG.warning("Read-through loader failed for '%s': %s", key, exc)
                self._metrics.record_error(region=self._region)

        self._metrics.record_miss(region=self._region)
        return None

    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """Return the raw CacheEntry (with metadata) or None."""
        entry, _ = self._get_entry(key)
        return entry

    def _get_entry(self, key: str) -> tuple[Optional[CacheEntry], str]:
        """Try each level in order; promote on hit. Returns (entry, level_str)."""
        entry = self._l1.get(key)
        if entry is not None:
            return entry, CacheLevel.L1.value

        if self._l2:
            entry = self._l2.get(key)
            if entry is not None:
                self._promote_to_l1(key, entry)
                return entry, CacheLevel.L2.value

        if self._l3:
            entry = self._l3.get(key)
            if entry is not None:
                self._promote_to_l2(key, entry)
                self._promote_to_l1(key, entry)
                return entry, CacheLevel.L3.value

        return None, ""

    # ── Core write ───────────────────────────────────────────────────────────

    def put(
        self,
        key: str,
        value: Any,
        *,
        ttl: Optional[float] = None,
        tags: Optional[set[str]] = None,
        priority: CachePriority = CachePriority.NORMAL,
        sliding_window: Optional[float] = None,
        size_bytes: int = 0,
        version: Optional[int] = None,
    ) -> bool:
        t0 = time.monotonic()
        effective_ttl = ttl if ttl is not None else self._default_ttl
        entry = make_entry(
            key, value,
            ttl=effective_ttl,
            tags=tags or set(),
            priority=priority,
            region=self._region,
            sliding_window=sliding_window,
            size_bytes=size_bytes,
        )
        if version is not None:
            entry.version = version

        ok = self._write(key, entry)
        ms = (time.monotonic() - t0) * 1000
        self._metrics.record_write(ms, region=self._region)
        return ok

    def put_entry(self, key: str, entry: CacheEntry) -> bool:
        """Write a pre-built CacheEntry directly."""
        return self._write(key, entry)

    def _write(self, key: str, entry: CacheEntry) -> bool:
        wp = self._write_policy
        if wp == WritePolicy.WRITE_THROUGH:
            self._l1.put(key, entry)
            if self._l2:
                self._l2.put(key, entry.clone_for_level(CacheLevel.L2))
            if self._l3:
                self._l3.put(key, entry.clone_for_level(CacheLevel.L3))
        elif wp == WritePolicy.WRITE_BACK:
            dirty = entry.clone_for_level(CacheLevel.L1)
            dirty.dirty = True
            self._l1.put(key, dirty)
        elif wp == WritePolicy.WRITE_AROUND:
            if self._l3:
                self._l3.put(key, entry.clone_for_level(CacheLevel.L3))
        return True

    # ── Versioned update (optimistic concurrency) ────────────────────────────

    def update(self, key: str, value: Any, expected_version: int, **kw: Any) -> bool:
        """Update a key only if its current version matches *expected_version*."""
        existing = self.get_entry(key)
        if existing is None or existing.version != expected_version:
            actual = existing.version if existing else 0
            raise CacheVersionConflictError(key, expected_version, actual)
        kw["version"] = expected_version + 1
        return self.put(key, value, **kw)

    # ── Delete ───────────────────────────────────────────────────────────────

    def delete(self, key: str) -> bool:
        deleted = self._l1.delete(key)
        if self._l2:
            deleted |= self._l2.delete(key)
        if self._l3:
            deleted |= self._l3.delete(key)
        if deleted:
            self._metrics.record_delete(region=self._region)
        return deleted

    def exists(self, key: str) -> bool:
        return self._l1.exists(key) or (self._l2 is not None and self._l2.exists(key))

    # ── Bulk operations ──────────────────────────────────────────────────────

    def get_multi(self, keys: list[str]) -> dict[str, Any]:
        """Bulk-get; returns only keys that are present."""
        result: dict[str, Any] = {}
        for k in keys:
            v = self.get(k)
            if v is not None:
                result[k] = v
        return result

    def put_multi(
        self,
        mapping: dict[str, Any],
        *,
        ttl: Optional[float] = None,
        tags: Optional[set[str]] = None,
    ) -> int:
        """Bulk-put; returns count written."""
        count = 0
        for key, value in mapping.items():
            if self.put(key, value, ttl=ttl, tags=tags or set()):
                count += 1
        return count

    def delete_multi(self, keys: list[str]) -> int:
        return sum(1 for k in keys if self.delete(k))

    # ── Tag-based invalidation ───────────────────────────────────────────────

    def invalidate_by_tag(self, tag: str) -> int:
        """Remove all entries bearing *tag* from every level."""
        total = 0
        for provider in self._providers():
            victims = [
                e.key for e in self._entries_of(provider)
                if tag in e.tags
            ]
            total += provider.delete_multi(victims)
        self._metrics.record_invalidation(total, region=self._region)
        return total

    def invalidate_by_tags(self, tags: set[str]) -> int:
        total = 0
        for tag in tags:
            total += self.invalidate_by_tag(tag)
        return total

    # ── Namespace / region clearing ──────────────────────────────────────────

    def clear_region(self) -> int:
        """Clear all entries from this engine's region across all levels."""
        total = 0
        for provider in self._providers():
            total += provider.clear()
        return total

    def clear_namespace(self, namespace: str) -> int:
        """Remove all keys that start with *namespace:*."""
        prefix = namespace if namespace.endswith(":") else namespace + ":"
        total = 0
        for provider in self._providers():
            victims = [k for k in provider.keys() if k.startswith(prefix)]
            total += provider.delete_multi(victims)
        return total

    # ── Increment / Decrement ────────────────────────────────────────────────

    def increment(self, key: str, delta: int = 1, default: int = 0) -> int:
        """Atomically increment a numeric cached value. Creates key if absent."""
        if isinstance(self._l1, L1MemoryProvider):
            val = self._l1.atomic_increment(key, delta=delta, default=default)
            # Propagate to L2/L3 if write-through
            if self._write_policy == WritePolicy.WRITE_THROUGH:
                entry = self._l1.get(key)
                if entry and self._l2:
                    self._l2.put(key, entry.clone_for_level(CacheLevel.L2))
            return val
        # Fallback for non-L1MemoryProvider
        current = self.get(key)
        if current is None:
            new_val = default + delta
        else:
            new_val = current + delta
        self.put(key, new_val)
        return new_val

    def decrement(self, key: str, delta: int = 1, default: int = 0) -> int:
        return self.increment(key, delta=-delta, default=default)

    # ── Write-back sync ──────────────────────────────────────────────────────

    def sync(self) -> SyncResult:
        """Flush dirty write-back entries to L2 and L3."""
        result = SyncResult()
        dirty_entries = [
            e for e in self._entries_of(self._l1) if e.dirty
        ]
        for entry in dirty_entries:
            try:
                if self._l2:
                    self._l2.put(entry.key, entry.clone_for_level(CacheLevel.L2))
                if self._l3:
                    self._l3.put(entry.key, entry.clone_for_level(CacheLevel.L3))
                entry.dirty = False
                result.flushed += 1
            except Exception as exc:
                result.failed += 1
                result.errors.append(str(exc))
                self._metrics.record_sync_failure()
        return result

    # ── Warm-up ──────────────────────────────────────────────────────────────

    def warm_up(
        self,
        data: dict[str, Any],
        *,
        ttl: Optional[float] = None,
        tags: Optional[set[str]] = None,
    ) -> int:
        """Pre-populate the cache with a dict of {key: value}."""
        return self.put_multi(data, ttl=ttl, tags=tags)

    # ── Replace ──────────────────────────────────────────────────────────────

    def replace(self, key: str, value: Any, **kw: Any) -> bool:
        """Update value only if key already exists."""
        if not self.exists(key):
            return False
        return self.put(key, value, **kw)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _providers(self) -> list[BaseCacheProvider]:
        providers = [self._l1]
        if self._l2:
            providers.append(self._l2)
        if self._l3:
            providers.append(self._l3)
        return providers

    def _entries_of(self, provider: BaseCacheProvider) -> list[CacheEntry]:
        entries: list[CacheEntry] = []
        for k in provider.keys():
            e = provider.get(k)
            if e is not None:
                entries.append(e)
        return entries

    def _promote_to_l1(self, key: str, entry: CacheEntry) -> None:
        promoted = entry.clone_for_level(CacheLevel.L1)
        self._l1.put(key, promoted)

    def _promote_to_l2(self, key: str, entry: CacheEntry) -> None:
        if self._l2:
            promoted = entry.clone_for_level(CacheLevel.L2)
            self._l2.put(key, promoted)

    def size(self) -> int:
        return self._l1.size()

    def keys(self) -> list[str]:
        return self._l1.keys()

    def stats_snapshot(self) -> dict[str, Any]:
        snap = self._metrics.snapshot()
        snap["l1"] = self._l1.stats().__dict__
        if self._l2:
            snap["l2"] = self._l2.stats().__dict__
        if self._l3:
            snap["l3"] = self._l3.stats().__dict__
        return snap
