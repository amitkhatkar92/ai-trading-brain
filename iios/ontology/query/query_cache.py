"""
iios/ontology/query/query_cache.py
===================================
Time-to-live LRU cache for query results.

Key design decisions:
* Cache key = deterministic hash of query target + type + filters.
* Each entry carries a TTL; expired entries are evicted lazily on access.
* Hit-rate and entry statistics are tracked for profiling.
* Thread-safe via a single RLock.
* Singleton: get_query_cache() / reset_query_cache()
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .query_constants import QUERY_CACHE_TTL_SECONDS, QUERY_CACHE_MAX_SIZE
from .query_exceptions import QueryCacheError

__all__ = [
    "QueryCacheEntry",
    "QueryCache",
    "get_query_cache",
    "reset_query_cache",
]


# ── Cache entry ───────────────────────────────────────────────────────────────

@dataclass
class QueryCacheEntry:
    key:        str
    result:     Any          # The cached payload (usually a list or dict)
    created_at: float        = field(default_factory=time.time)
    ttl:        float        = float(QUERY_CACHE_TTL_SECONDS)
    hit_count:  int          = 0
    result_type: str         = ""

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def to_dict(self) -> dict:
        return {
            "key":         self.key,
            "result_type": self.result_type,
            "created_at":  self.created_at,
            "ttl":         self.ttl,
            "hit_count":   self.hit_count,
            "age_seconds": round(self.age_seconds, 2),
            "is_expired":  self.is_expired,
        }


# ── Cache ─────────────────────────────────────────────────────────────────────

class QueryCache:
    """
    Thread-safe LRU query-result cache.

    Usage::

        cache = get_query_cache()
        key   = cache.make_key("type_lookup", "iios.entity.Instrument")
        if cache.has(key):
            return cache.get(key)
        result = expensive_query()
        cache.put(key, result)
    """

    def __init__(
        self,
        default_ttl: float = float(QUERY_CACHE_TTL_SECONDS),
        max_size:    int   = QUERY_CACHE_MAX_SIZE,
    ) -> None:
        self._default_ttl = default_ttl
        self._max_size    = max_size
        self._entries:    dict[str, QueryCacheEntry] = {}
        self._order:      list[str]                  = []  # LRU order, newest at end
        self._hits        = 0
        self._misses      = 0
        self._evictions   = 0
        self._lock        = threading.RLock()

    # ── Key construction ──────────────────────────────────────────────────────

    @staticmethod
    def make_key(*parts: Any) -> str:
        """Create a deterministic cache key from arbitrary parts."""
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()

    # ── Core operations ───────────────────────────────────────────────────────

    def put(
        self,
        key:         str,
        result:      Any,
        ttl:         Optional[float] = None,
        result_type: str             = "",
    ) -> None:
        """Store *result* under *key*."""
        with self._lock:
            ttl_val = ttl if ttl is not None else self._default_ttl
            entry   = QueryCacheEntry(
                key         = key,
                result      = result,
                ttl         = ttl_val,
                result_type = result_type,
            )
            if key in self._entries:
                self._order.remove(key)
            self._entries[key] = entry
            self._order.append(key)
            self._evict_if_needed()

    def get(self, key: str) -> Optional[Any]:
        """Return the cached result or None if missing / expired."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                self._delete(key)
                self._misses += 1
                return None
            # Move to end (most-recently used)
            self._order.remove(key)
            self._order.append(key)
            entry.hit_count += 1
            self._hits += 1
            return entry.result

    def has(self, key: str) -> bool:
        """Return True if *key* is present and not expired."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                self._delete(key)
                return False
            return True

    def invalidate(self, key: str) -> bool:
        """Remove a single entry. Returns True if it existed."""
        with self._lock:
            if key in self._entries:
                self._delete(key)
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all entries whose key starts with *prefix*. Returns count removed."""
        with self._lock:
            to_remove = [k for k in list(self._entries) if k.startswith(prefix)]
            for k in to_remove:
                self._delete(k)
            return len(to_remove)

    def invalidate_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._lock:
            expired = [k for k, e in self._entries.items() if e.is_expired]
            for k in expired:
                self._delete(k)
            return len(expired)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._order.clear()

    # ── Statistics ────────────────────────────────────────────────────────────

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return (self._hits / total) if total > 0 else 0.0

    def stats(self) -> dict:
        with self._lock:
            valid   = sum(1 for e in self._entries.values() if not e.is_expired)
            expired = len(self._entries) - valid
            return {
                "size":      len(self._entries),
                "valid":     valid,
                "expired":   expired,
                "max_size":  self._max_size,
                "hits":      self._hits,
                "misses":    self._misses,
                "evictions": self._evictions,
                "hit_rate":  round(self.hit_rate, 4),
            }

    def entry_info(self, key: str) -> Optional[dict]:
        with self._lock:
            entry = self._entries.get(key)
            return entry.to_dict() if entry else None

    # ── Private helpers ───────────────────────────────────────────────────────

    def _delete(self, key: str) -> None:
        """Remove entry; caller must hold lock."""
        self._entries.pop(key, None)
        try:
            self._order.remove(key)
        except ValueError:
            pass

    def _evict_if_needed(self) -> None:
        """Evict LRU entries until size ≤ max_size; caller must hold lock."""
        while len(self._entries) > self._max_size:
            if not self._order:
                break
            lru_key = self._order[0]
            self._delete(lru_key)
            self._evictions += 1


# ── Singleton ─────────────────────────────────────────────────────────────────

_cache_lock = threading.Lock()
_cache_instance: Optional[QueryCache] = None


def get_query_cache(
    default_ttl: float = float(QUERY_CACHE_TTL_SECONDS),
    max_size:    int   = QUERY_CACHE_MAX_SIZE,
) -> QueryCache:
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = QueryCache(
                    default_ttl = default_ttl,
                    max_size    = max_size,
                )
    return _cache_instance


def reset_query_cache() -> None:
    global _cache_instance
    with _cache_lock:
        _cache_instance = None
