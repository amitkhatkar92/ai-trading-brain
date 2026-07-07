"""
iios/knowledge/search/search_engine.py
========================================
Core SearchEngine: validates → optimizes → cache-checks → executes → ranks → paginates.

Responsibilities:
  • Tie together QueryValidator, QueryOptimizer, QueryExecutor
  • Apply RankingStrategy to raw results
  • Maintain an LRU + TTL search result cache
  • Record statistics via SearchStats
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import OrderedDict
from dataclasses import replace
from typing import Any, Optional

from .search_constants import (
    RankingStrategy, SearchType,
    SEARCH_CACHE_TTL, SEARCH_CACHE_MAX_SIZE,
    RECENCY_DECAY_DAYS,
)
from .search_exceptions import SearchEngineError
from .index_manager     import IndexManager,    get_index_manager
from .query_validator   import QueryValidator,  get_query_validator
from .query_optimizer   import QueryOptimizer,  get_query_optimizer
from .query_executor    import QueryExecutor,   get_query_executor
from .index_statistics  import SearchStats,     get_search_stats
from .models.unified_query  import UnifiedSearchQuery
from .models.unified_result import UnifiedSearchResult
from .models.search_response import SearchResponse

__all__ = ["SearchEngine", "get_search_engine", "reset_search_engine"]

_LOG  = logging.getLogger("iios.knowledge.search.engine")
_lock = threading.Lock()
_engine: Optional["SearchEngine"] = None


# ── Search result cache ────────────────────────────────────────────────────────

class _SearchCache:
    """LRU + TTL cache keyed on query.cache_key()."""

    def __init__(self, max_size: int = SEARCH_CACHE_MAX_SIZE, ttl: float = SEARCH_CACHE_TTL) -> None:
        self._max_size = max_size
        self._ttl      = ttl
        self._store:  OrderedDict[str, tuple[SearchResponse, float]] = OrderedDict()
        self._lock    = threading.RLock()
        self.hits     = 0
        self.misses   = 0

    def get(self, key: str) -> Optional[SearchResponse]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            response, ts = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[key]
                self.misses += 1
                return None
            # LRU: move to end
            self._store.move_to_end(key)
            self.hits += 1
            return replace(response, cache_hit=True)

    def put(self, key: str, response: SearchResponse) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            elif len(self._store) >= self._max_size:
                self._store.popitem(last=False)  # evict oldest
            self._store[key] = (response, time.monotonic())

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits   = 0
            self.misses = 0

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)


# ── Ranking ───────────────────────────────────────────────────────────────────

def _rank_results(
    results:   list[UnifiedSearchResult],
    strategy:  RankingStrategy,
    idx:       IndexManager,
    now:       float,
) -> list[UnifiedSearchResult]:
    """Apply ranking strategy and return sorted (descending) results."""
    if not results:
        return []

    total = len(results)

    # Pre-compute per-item signals
    for r in results:
        age_days  = max(0.0, (now - r.updated_at) / 86400.0)
        recency   = max(0.0, 1.0 - age_days / RECENCY_DECAY_DAYS)
        popularity = idx.keyword_token_count()  # crude importance proxy

        if strategy == RankingStrategy.RELEVANCE:
            final = r.score
        elif strategy == RankingStrategy.CONFIDENCE:
            final = r.confidence
        elif strategy == RankingStrategy.RECENCY:
            final = recency
        elif strategy == RankingStrategy.IMPORTANCE:
            # Favour items with more metadata / tag richness
            richness = len(r.tags) * 0.1 + len(r.metadata) * 0.05
            final = r.confidence * 0.5 + richness
        elif strategy == RankingStrategy.RELATIONSHIP_STRENGTH:
            # Use weight stored in metadata if present (graph nodes)
            weight = float(r.metadata.get("weight", 0.5))
            final  = weight * r.confidence
        elif strategy == RankingStrategy.HYBRID:
            final = (
                0.50 * r.score
                + 0.20 * r.confidence
                + 0.15 * recency
                + 0.15 * (len(r.tags) / max(10, 1))  # tag richness
            )
        else:  # CUSTOM → fall back to score
            final = r.score

        object.__setattr__(r, "score", final) if hasattr(r, "__dataclass_fields__") else setattr(r, "score", final)

    return sorted(results, key=lambda x: x.score, reverse=True)


def _post_rank_score(
    results: list[UnifiedSearchResult],
    strategy: RankingStrategy,
    idx: IndexManager,
) -> list[UnifiedSearchResult]:
    now = time.time()
    return _rank_results(results, strategy, idx, now)


# ── Engine ────────────────────────────────────────────────────────────────────

class SearchEngine:
    """
    Primary search pipeline.

    Usage::

        engine   = get_search_engine()
        response = engine.search(UnifiedSearchQuery(text="NIFTY 50 trend"))
        print(response.total, [r.title for r in response.results])
    """

    def __init__(
        self,
        index_manager:   Optional[IndexManager]   = None,
        query_validator: Optional[QueryValidator] = None,
        query_optimizer: Optional[QueryOptimizer] = None,
        query_executor:  Optional[QueryExecutor]  = None,
        stats:           Optional[SearchStats]    = None,
    ) -> None:
        self._idx        = index_manager   or get_index_manager()
        self._validator  = query_validator or get_query_validator()
        self._optimizer  = query_optimizer or get_query_optimizer()
        self._executor   = query_executor  or get_query_executor()
        self._stats      = stats           or get_search_stats()
        self._cache      = _SearchCache()
        self._lock       = threading.RLock()

    # ── Public API ────────────────────────────────────────────────────────────

    def search(self, query: UnifiedSearchQuery) -> SearchResponse:
        """Full pipeline: validate → optimize → cache? → execute → rank → paginate."""
        start = time.perf_counter()

        # Validate
        violations = self._validator.validate(query)
        warnings: list[str] = []
        if violations:
            warnings = violations  # report but don't abort (soft validation)

        # Optimize
        optimized = self._optimizer.optimize(query)

        # Cache check
        cache_key = optimized.cache_key()
        cached    = self._cache.get(cache_key)
        if cached is not None:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._stats.record_query(elapsed_ms, cache_hit=True)
            return cached

        # Execute
        raw_results, indexes_used = self._executor.execute(optimized)

        # Apply score gate
        if optimized.min_score > 0.0:
            raw_results = [r for r in raw_results if r.score >= optimized.min_score]

        # Rank
        ranked = _post_rank_score(raw_results, optimized.ranking_strategy, self._idx)

        # Assemble response (includes pagination)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response   = SearchResponse.build(
            query             = optimized,
            ranked_results    = ranked,
            total             = len(ranked),
            execution_time_ms = elapsed_ms,
            cache_hit         = False,
            indexes_used      = indexes_used,
            warnings          = warnings,
        )

        # Cache
        self._cache.put(cache_key, response)

        self._stats.record_query(elapsed_ms, cache_hit=False)
        return response

    def invalidate_cache(self) -> None:
        self._cache.clear()

    def cache_stats(self) -> dict[str, Any]:
        return {
            "size":    self._cache.size,
            "hits":    self._cache.hits,
            "misses":  self._cache.misses,
            "max_size": self._cache.max_size if hasattr(self._cache, "max_size") else SEARCH_CACHE_MAX_SIZE,
        }

    def statistics(self) -> dict[str, Any]:
        return {
            "engine":  "SearchEngine",
            "cache":   self.cache_stats(),
            "queries": self._stats.to_dict(),
            "index":   self._idx.statistics(),
        }


def get_search_engine() -> SearchEngine:
    global _engine
    with _lock:
        if _engine is None:
            _engine = SearchEngine()
        return _engine


def reset_search_engine() -> None:
    global _engine
    with _lock:
        _engine = None
