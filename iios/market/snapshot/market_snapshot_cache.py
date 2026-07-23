"""
market_snapshot_cache.py — iios.market.snapshot
================================================
TTL-based snapshot cache for fast recent-snapshot retrieval.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Dict, Optional, Tuple

from .constants import DEFAULT_CACHE_TTL_S, DEFAULT_MAX_CACHE
from .market_snapshot import MarketSnapshot


class MarketSnapshotCache:
    """
    Thread-safe TTL cache keyed by a ``(exchange, key)`` tuple.

    Default *key* is ``"latest"`` — used for the most recent published
    snapshot per exchange.  Entries expire after ``ttl_s`` seconds.
    When ``max_entries`` is reached, the oldest entry is evicted (FIFO).
    """

    def __init__(
        self,
        ttl_s:       float = DEFAULT_CACHE_TTL_S,
        max_entries: int   = DEFAULT_MAX_CACHE,
    ) -> None:
        self._ttl   = ttl_s
        self._max   = max_entries
        self._lock  = threading.RLock()
        # value: (snapshot, expiry_timestamp)
        self._data: OrderedDict[str, Tuple[MarketSnapshot, float]] = OrderedDict()
        self._hits:   int = 0
        self._misses: int = 0

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def put(
        self,
        snapshot: MarketSnapshot,
        *,
        key: str = "latest",
        ttl_s:   Optional[float] = None,
    ) -> None:
        cache_key = self._make_key(snapshot.exchange, key)
        expiry    = time.time() + (ttl_s if ttl_s is not None else self._ttl)
        with self._lock:
            if cache_key in self._data:
                del self._data[cache_key]
            elif len(self._data) >= self._max:
                self._data.popitem(last=False)
            self._data[cache_key] = (snapshot, expiry)

    def invalidate(self, exchange: str, key: str = "latest") -> bool:
        with self._lock:
            cache_key = self._make_key(exchange, key)
            if cache_key in self._data:
                del self._data[cache_key]
                return True
            return False

    def invalidate_all_for_exchange(self, exchange: str) -> int:
        prefix = f"{exchange}:"
        with self._lock:
            keys = [k for k in self._data if k.startswith(prefix)]
            for k in keys:
                del self._data[k]
            return len(keys)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(
        self,
        exchange: str,
        key: str = "latest",
    ) -> Optional[MarketSnapshot]:
        cache_key = self._make_key(exchange, key)
        with self._lock:
            entry = self._data.get(cache_key)
            if entry is None:
                self._misses += 1
                return None
            snapshot, expiry = entry
            if time.time() > expiry:
                del self._data[cache_key]
                self._misses += 1
                return None
            self._hits += 1
            return snapshot

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def evict_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._data.items() if now > exp]
            for k in expired:
                del self._data[k]
            return len(expired)

    def stats(self) -> Dict[str, object]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits":       self._hits,
                "misses":     self._misses,
                "hit_rate":   round(self._hits / total, 4) if total > 0 else 0.0,
                "size":       len(self._data),
                "max_entries": self._max,
            }

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._hits   = 0
            self._misses = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(exchange: str, key: str) -> str:
        return f"{exchange}:{key}"
