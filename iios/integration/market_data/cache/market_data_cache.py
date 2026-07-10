"""iios/integration/market_data/cache/market_data_cache.py

Thread-safe TTL + LRU cache for market data records.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

V = TypeVar("V")

_DEFAULT_QUOTE_TTL    = 5.0       # seconds
_DEFAULT_CANDLE_TTL   = 60.0
_DEFAULT_SNAPSHOT_TTL = 10.0
_DEFAULT_HISTORY_TTL  = 300.0
_DEFAULT_MAX_ENTRIES  = 100_000


@dataclass
class CacheEntry(Generic[V]):
    value:      V
    expires_at: float
    hits:       int = 0


class MarketDataCache(Generic[V]):
    """
    Generic TTL + LRU cache for market data payloads.

    Keys are strings (typically ``symbol:interval`` or ``symbol:type``).
    """

    def __init__(
        self,
        max_entries: int   = _DEFAULT_MAX_ENTRIES,
        default_ttl: float = _DEFAULT_QUOTE_TTL,
        name:        str   = "market_cache",
    ) -> None:
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self.name         = name
        self._lock        = threading.RLock()
        self._cache: OrderedDict[str, CacheEntry[V]] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "expirations": 0}

    # ── Write ──────────────────────────────────────────────────────────────────

    def put(self, key: str, value: V, ttl_sec: float | None = None) -> None:
        ttl = ttl_sec if ttl_sec is not None else self._default_ttl
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = CacheEntry(value=value, expires_at=time.time() + ttl)
            # Evict oldest if over capacity
            while len(self._cache) > self._max_entries:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1

    # ── Read ───────────────────────────────────────────────────────────────────

    def get(self, key: str) -> V | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats["hits"] += 1
            return entry.value

    # ── Invalidation ───────────────────────────────────────────────────────────

    def invalidate(self, key: str) -> bool:
        with self._lock:
            return self._cache.pop(key, None) is not None

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def purge_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, e in self._cache.items() if now > e.expires_at]
            for k in expired:
                del self._cache[k]
                self._stats["expirations"] += 1
            return len(expired)

    # ── Inspection ─────────────────────────────────────────────────────────────

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name":        self.name,
                "size":        len(self._cache),
                "max_entries": self._max_entries,
                **self._stats,
            }
