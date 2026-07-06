"""
iios/infrastructure/database/performance/query_cache.py
========================================================
Query result cache with TTL and LRU eviction.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

from ..database_connection import Row
from ..database_constants import DEFAULT_QUERY_CACHE_SIZE, DEFAULT_QUERY_CACHE_TTL

__all__ = ["QueryCache", "CacheStats"]


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    current_size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def reset(self) -> None:
        self.hits = self.misses = self.evictions = self.expirations = 0


@dataclass
class _CacheEntry:
    rows: list[Row]
    created_at: float
    ttl: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.monotonic)

    @property
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return time.monotonic() - self.created_at >= self.ttl

    def touch(self) -> None:
        self.access_count += 1
        self.last_accessed = time.monotonic()


class QueryCache:
    """LRU + TTL cache for SELECT query results.

    Keyed by ``(sql, params)``.  Cache is invalidated per-table when any
    write (INSERT/UPDATE/DELETE) is detected on that table.

    Usage::

        cache = QueryCache(max_size=500, default_ttl=60.0)
        rows = cache.get(sql, params)
        if rows is None:
            rows = db.query(sql, params)
            cache.set(sql, params, rows, tables=["trades"])
    """

    def __init__(
        self,
        max_size: int = DEFAULT_QUERY_CACHE_SIZE,
        default_ttl: float = DEFAULT_QUERY_CACHE_TTL,
        exclude_tables: Optional[list[str]] = None,
    ) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._exclude = set(exclude_tables or [])
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._table_keys: dict[str, set[str]] = {}  # table → {cache_key, ...}
        self._stats = CacheStats()
        self._lock = threading.RLock()

    # ── Public interface ──────────────────────────────────────────────────────

    def get(self, sql: str, params: tuple = ()) -> Optional[list[Row]]:
        key = self._make_key(sql, params)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            if entry.is_expired:
                self._evict_key(key)
                self._stats.expirations += 1
                self._stats.misses += 1
                return None
            # LRU: move to end
            self._entries.move_to_end(key)
            entry.touch()
            self._stats.hits += 1
            return list(entry.rows)

    def set(
        self,
        sql: str,
        params: tuple = (),
        rows: Optional[list[Row]] = None,
        tables: Optional[list[str]] = None,
        ttl: Optional[float] = None,
    ) -> None:
        if rows is None:
            return
        # Don't cache queries on excluded tables
        if tables and any(t in self._exclude for t in tables):
            return
        key = self._make_key(sql, params)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            if key in self._entries:
                del self._entries[key]
            entry = _CacheEntry(
                rows=list(rows),
                created_at=time.monotonic(),
                ttl=effective_ttl,
            )
            self._entries[key] = entry
            self._entries.move_to_end(key)
            # Track table → key mapping
            for table in (tables or []):
                self._table_keys.setdefault(table, set()).add(key)
            # Evict if over capacity
            while len(self._entries) > self._max_size:
                oldest_key = next(iter(self._entries))
                self._evict_key(oldest_key)
                self._stats.evictions += 1
            self._stats.current_size = len(self._entries)

    def invalidate_table(self, table: str) -> int:
        """Invalidate all cached results that touch *table*."""
        with self._lock:
            keys = list(self._table_keys.pop(table, set()))
            for key in keys:
                self._entries.pop(key, None)
            self._stats.current_size = len(self._entries)
            return len(keys)

    def invalidate_all(self) -> None:
        with self._lock:
            self._entries.clear()
            self._table_keys.clear()
            self._stats.current_size = 0

    def purge_expired(self) -> int:
        with self._lock:
            expired = [k for k, e in self._entries.items() if e.is_expired]
            for k in expired:
                self._evict_key(k)
                self._stats.expirations += 1
            return len(expired)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    @property
    def stats(self) -> CacheStats:
        with self._lock:
            self._stats.current_size = len(self._entries)
            return self._stats

    def reset_stats(self) -> None:
        with self._lock:
            self._stats.reset()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _make_key(self, sql: str, params: tuple) -> str:
        raw = json.dumps([sql, list(params)], sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _evict_key(self, key: str) -> None:
        self._entries.pop(key, None)
        # Clean up table index
        for table_keys in self._table_keys.values():
            table_keys.discard(key)
