"""
iios/knowledge/search/index_statistics.py
==========================================
Tracks per-index and global search engine statistics at runtime.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from .models.index_definition import IndexStatistics

__all__ = ["SearchStats", "get_search_stats", "reset_search_stats"]

_lock:  threading.Lock             = threading.Lock()
_stats: Optional["SearchStats"]    = None


class SearchStats:
    """Aggregates runtime statistics across all search operations."""

    def __init__(self) -> None:
        self._lock           = threading.RLock()
        self._per_index:     dict[str, IndexStatistics] = {}
        self._total_queries  = 0
        self._total_cache_hits = 0
        self._total_cache_misses = 0
        self._total_exec_ms  = 0.0
        self._last_query_at: Optional[float] = None

    def get_or_create(self, index_id: str, name: str) -> IndexStatistics:
        with self._lock:
            if index_id not in self._per_index:
                self._per_index[index_id] = IndexStatistics(index_id=index_id, name=name)
            return self._per_index[index_id]

    def record_query(
        self,
        execution_time_ms: float,
        cache_hit:         bool,
        index_id:          str  = "global",
        name:              str  = "global",
    ) -> None:
        with self._lock:
            self._total_queries += 1
            self._total_exec_ms += execution_time_ms
            self._last_query_at  = time.time()
            if cache_hit:
                self._total_cache_hits += 1
            else:
                self._total_cache_misses += 1
            s = self._per_index.setdefault(
                index_id, IndexStatistics(index_id=index_id, name=name),
            )
            s.record_query(execution_time_ms, cache_hit)

    def record_index_built(
        self,
        index_id:      str,
        name:          str,
        item_count:    int,
        build_time_ms: float,
    ) -> None:
        with self._lock:
            s = self._per_index.setdefault(
                index_id, IndexStatistics(index_id=index_id, name=name),
            )
            s.item_count     = item_count
            s.build_time_ms  = build_time_ms
            s.last_rebuilt   = time.time()

    @property
    def total_queries(self) -> int:
        with self._lock:
            return self._total_queries

    @property
    def avg_exec_ms(self) -> float:
        with self._lock:
            return self._total_exec_ms / self._total_queries if self._total_queries else 0.0

    @property
    def cache_hit_ratio(self) -> float:
        with self._lock:
            total = self._total_cache_hits + self._total_cache_misses
            return self._total_cache_hits / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_queries":    self._total_queries,
                "total_cache_hits": self._total_cache_hits,
                "cache_hit_ratio":  round(self.cache_hit_ratio, 4),
                "avg_exec_ms":      round(self.avg_exec_ms, 3),
                "last_query_at":    self._last_query_at,
                "per_index":        {k: v.to_dict() for k, v in self._per_index.items()},
            }

    def reset(self) -> None:
        with self._lock:
            self._per_index.clear()
            self._total_queries      = 0
            self._total_cache_hits   = 0
            self._total_cache_misses = 0
            self._total_exec_ms      = 0.0
            self._last_query_at      = None


def get_search_stats() -> SearchStats:
    global _stats
    with _lock:
        if _stats is None:
            _stats = SearchStats()
        return _stats


def reset_search_stats() -> None:
    global _stats
    with _lock:
        _stats = None
