"""iios/integration/history/cache/__init__.py

TTL/LRU in-memory cache for historical records and query results.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.integration.history.history_constants import (
    DEFAULT_CACHE_MAX_RECORDS,
    DEFAULT_CACHE_TTL_SEC,
)


class HistoryCache:
    """
    Thread-safe LRU/TTL cache.

    Caches anything JSON-serialisable: records, query results, snapshots.
    Items expire after ``ttl_sec`` seconds; oldest items are evicted when
    capacity is reached.
    """

    def __init__(
        self,
        max_size: int = DEFAULT_CACHE_MAX_RECORDS,
        ttl_sec:  int = DEFAULT_CACHE_TTL_SEC,
    ) -> None:
        self._max  = max_size
        self._ttl  = ttl_sec
        self._lock = threading.RLock()
        self._store: dict[str, tuple[Any, float]] = {}
        self._order: list[str] = []
        self._stats: dict[str, int] = {
            "hits": 0, "misses": 0, "inserts": 0, "evictions": 0,
        }

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._order.remove(key)
            elif len(self._store) >= self._max:
                oldest = self._order.pop(0)
                del self._store[oldest]
                self._stats["evictions"] += 1
            self._store[key] = (value, time.time())
            self._order.append(key)
            self._stats["inserts"] += 1

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            value, ts = entry
            if time.time() - ts > self._ttl:
                del self._store[key]
                if key in self._order:
                    self._order.remove(key)
                self._stats["misses"] += 1
                return None
            self._stats["hits"] += 1
            return value

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)
            if key in self._order:
                self._order.remove(key)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._order.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
