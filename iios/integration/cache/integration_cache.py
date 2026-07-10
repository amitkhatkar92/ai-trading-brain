"""iios/integration/cache/integration_cache.py

TTL-based, thread-safe in-memory cache for integration layer data.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.integration.integration_constants import DEFAULT_CACHE_MAX_ENTRIES, DEFAULT_CACHE_TTL_SEC
from iios.integration.integration_exceptions import CacheOverflowError
from iios.integration.cache.cache_entry import CacheEntry
from iios.integration.cache.cache_key import CacheKey


class IntegrationCache:
    """
    In-process, thread-safe TTL cache.

    - put(key, value, ttl_sec) — stores a value
    - get(key)                 — returns value or None on miss/expiry
    - LRU eviction when max_entries is reached

    The cache is intentionally simple to remain replaceable with Redis,
    Memcached, etc. at deployment time.
    """

    def __init__(
        self,
        max_entries: int   = DEFAULT_CACHE_MAX_ENTRIES,
        default_ttl: float = DEFAULT_CACHE_TTL_SEC,
    ) -> None:
        self._max       = max_entries
        self._default_ttl = default_ttl
        self._store:    dict[str, CacheEntry] = {}
        self._access_order: list[str]         = []   # LRU list
        self._hits   = 0
        self._misses = 0
        self._lock   = threading.RLock()

    # ── Write ──────────────────────────────────────────────────────────────────

    def put(
        self,
        key:     str | CacheKey,
        value:   Any,
        ttl_sec: float | None = None,
    ) -> None:
        k = key.to_hash() if isinstance(key, CacheKey) else str(key)
        ttl = ttl_sec if ttl_sec is not None else self._default_ttl
        with self._lock:
            if k in self._store:
                self._store[k] = CacheEntry(k, value, ttl)
                return
            if len(self._store) >= self._max:
                self._evict_one()
            self._store[k] = CacheEntry(k, value, ttl)
            self._access_order.append(k)

    def _evict_one(self) -> None:
        """Evict the LRU (oldest) entry."""
        if self._access_order:
            lru = self._access_order.pop(0)
            self._store.pop(lru, None)

    # ── Read ───────────────────────────────────────────────────────────────────

    def get(self, key: str | CacheKey) -> Any | None:
        k = key.to_hash() if isinstance(key, CacheKey) else str(key)
        with self._lock:
            entry = self._store.get(k)
            if entry is None or entry.is_expired():
                self._misses += 1
                if entry:
                    self._store.pop(k, None)
                    try:
                        self._access_order.remove(k)
                    except ValueError:
                        pass
                return None
            entry.touch()
            # Move to end of LRU list
            try:
                self._access_order.remove(k)
            except ValueError:
                pass
            self._access_order.append(k)
            self._hits += 1
            return entry.value

    def has(self, key: str | CacheKey) -> bool:
        return self.get(key) is not None

    # ── Invalidation ──────────────────────────────────────────────────────────

    def invalidate(self, key: str | CacheKey) -> None:
        k = key.to_hash() if isinstance(key, CacheKey) else str(key)
        with self._lock:
            self._store.pop(k, None)
            try:
                self._access_order.remove(k)
            except ValueError:
                pass

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._access_order.clear()

    def purge_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, e in self._store.items() if e.is_expired(now)]
            for k in expired:
                self._store.pop(k)
                try:
                    self._access_order.remove(k)
                except ValueError:
                    pass
        return len(expired)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size":        len(self._store),
                "max_entries": self._max,
                "hits":        self._hits,
                "misses":      self._misses,
                "hit_rate":    round(self._hits / total, 4) if total else 0.0,
                "default_ttl": self._default_ttl,
            }
