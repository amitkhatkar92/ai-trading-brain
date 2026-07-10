"""iios/integration/news/cache/__init__.py

In-memory LRU/TTL article cache for the news framework.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.integration.news.news_constants import DEFAULT_STALE_ARTICLE_SEC


class NewsDataCache:
    """
    Thread-safe in-memory cache for NewsArticle objects (and any JSON-serialisable
    payload).

    Cache items expire after ``ttl_sec`` seconds.
    Capacity is capped at ``max_size`` items; oldest entries are evicted first.
    """

    def __init__(
        self,
        max_size: int = 10_000,
        ttl_sec:  int = DEFAULT_STALE_ARTICLE_SEC,
    ) -> None:
        self._max_size = max_size
        self._ttl      = ttl_sec
        self._lock     = threading.RLock()
        # key → (value, inserted_at)
        self._store:   dict[str, tuple[Any, float]] = {}
        self._order:   list[str] = []    # insertion order for LRU eviction
        self._stats: dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0, "inserts": 0}

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._order.remove(key)
            elif len(self._store) >= self._max_size:
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
                self._store.pop(key, None)
                self._order.remove(key)
                self._stats["misses"] += 1
                return None
            self._stats["hits"] += 1
            return value

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._store:
                del self._store[key]
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
