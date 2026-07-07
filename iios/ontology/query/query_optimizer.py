"""
iios/ontology/query/query_optimizer.py
=======================================
Query planner and optimizer.

The optimizer analyses a QueryRequest and produces a QueryPlan that
describes how to execute it efficiently:

* Selects the cheapest index to use for candidate retrieval
* Applies filter ordering (selectivity-first)
* Enables parallel execution for large candidate sets
* Decides whether the cache should be checked first

It does NOT execute anything — it only plans.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .query_constants import (
    QueryType,
    IndexHint,
    DEFAULT_RESULT_LIMIT,
    QUERY_CACHE_TTL_SECONDS,
)
from .query_factory import QueryRequest

__all__ = [
    "OptimizationStep",
    "QueryPlan",
    "QueryOptimizer",
    "get_query_optimizer",
    "reset_query_optimizer",
]


# ── Optimization step ─────────────────────────────────────────────────────────

@dataclass
class OptimizationStep:
    """A single step in the query execution plan."""
    step_name:       str
    index_hint:      IndexHint
    estimated_cost:  float      = 1.0       # Relative cost (lower is better)
    parallelizable:  bool       = False
    description:     str        = ""

    def to_dict(self) -> dict:
        return {
            "step_name":      self.step_name,
            "index_hint":     self.index_hint.value,
            "estimated_cost": self.estimated_cost,
            "parallelizable": self.parallelizable,
            "description":    self.description,
        }


# ── Query plan ────────────────────────────────────────────────────────────────

@dataclass
class QueryPlan:
    """
    Execution plan produced by the optimizer for a single QueryRequest.
    """
    query_id:       str
    steps:          list[OptimizationStep] = field(default_factory=list)
    estimated_cost: float                  = 1.0
    use_cache:      bool                   = True
    cache_ttl:      float                  = float(QUERY_CACHE_TTL_SECONDS)
    parallel:       bool                   = False
    optimized:      bool                   = False
    index_hint:     IndexHint              = IndexHint.FULL_SCAN
    notes:          list[str]              = field(default_factory=list)

    @property
    def primary_index(self) -> IndexHint:
        return self.steps[0].index_hint if self.steps else self.index_hint

    def to_dict(self) -> dict:
        return {
            "query_id":       self.query_id,
            "steps":          [s.to_dict() for s in self.steps],
            "estimated_cost": round(self.estimated_cost, 4),
            "use_cache":      self.use_cache,
            "cache_ttl":      self.cache_ttl,
            "parallel":       self.parallel,
            "optimized":      self.optimized,
            "index_hint":     self.index_hint.value,
            "notes":          self.notes,
        }


# ── Optimizer ────────────────────────────────────────────────────────────────

class QueryOptimizer:
    """
    Stateless query planner.

    Usage::

        optimizer = get_query_optimizer()
        plan = optimizer.plan(request)
        if plan.use_cache:
            ...
    """

    def __init__(self) -> None:
        self._plan_count = 0
        self._total_ms   = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def plan(self, request: QueryRequest) -> QueryPlan:
        """Analyse *request* and return an execution plan."""
        t0 = time.perf_counter()
        self._plan_count += 1

        plan = self._build_plan(request)

        elapsed = (time.perf_counter() - t0) * 1_000.0
        self._total_ms += elapsed
        return plan

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_plan(self, req: QueryRequest) -> QueryPlan:
        qt    = req.query_type
        steps: list[OptimizationStep] = []
        notes: list[str]              = []

        # ── 1.  Index selection ────────────────────────────────────────────
        if qt == QueryType.TYPE_LOOKUP:
            primary = self._index_for_lookup(req.target, req.namespace_hint)
        elif qt in (QueryType.HIERARCHY, QueryType.ANCESTORS,
                    QueryType.DESCENDANTS, QueryType.CHILDREN,
                    QueryType.PARENT):
            primary = IndexHint.HIERARCHY_INDEX
        elif qt == QueryType.SEARCH or qt == QueryType.SEMANTIC:
            primary = IndexHint.FULL_SCAN
            notes.append("Full-scan required for text / semantic queries.")
        elif qt == QueryType.RELATIONSHIP_LOOKUP:
            primary = IndexHint.USE_URI_INDEX
        else:
            primary = IndexHint.FULL_SCAN

        steps.append(OptimizationStep(
            step_name      = "candidate_retrieval",
            index_hint     = primary,
            estimated_cost = self._cost_for_index(primary),
            description    = f"Retrieve candidates using {primary.value}",
        ))

        # ── 2.  Namespace pre-filter ───────────────────────────────────────
        if req.namespace_hint:
            steps.append(OptimizationStep(
                step_name      = "namespace_filter",
                index_hint     = IndexHint.USE_NAMESPACE_INDEX,
                estimated_cost = 0.1,
                description    = f"Restrict to namespace: {req.namespace_hint}",
            ))
            notes.append(f"Namespace filter applied: {req.namespace_hint}")

        # ── 3.  Abstract / deprecated pre-filter ──────────────────────────
        if not req.include_abstract or not req.include_deprecated:
            steps.append(OptimizationStep(
                step_name      = "visibility_filter",
                index_hint     = IndexHint.FULL_SCAN,
                estimated_cost = 0.05,
                description    = "Filter out abstract / deprecated types.",
            ))

        # ── 4.  Scoring / sorting ──────────────────────────────────────────
        if qt in (QueryType.SEARCH, QueryType.SEMANTIC):
            steps.append(OptimizationStep(
                step_name       = "semantic_rank",
                index_hint      = IndexHint.FULL_SCAN,
                estimated_cost  = 0.5,
                parallelizable  = True,
                description     = "Compute relevance scores and rank results.",
            ))

        # ── 5.  Result limit ───────────────────────────────────────────────
        steps.append(OptimizationStep(
            step_name      = "limit",
            index_hint     = IndexHint.FULL_SCAN,
            estimated_cost = 0.01,
            description    = f"Truncate to limit={req.limit}",
        ))

        # ── Cache policy ───────────────────────────────────────────────────
        use_cache = qt not in (QueryType.CROSS_REFERENCE,)
        cache_ttl = self._ttl_for_type(qt)

        # ── Parallelism ────────────────────────────────────────────────────
        parallel = any(s.parallelizable for s in steps)

        total_cost = sum(s.estimated_cost for s in steps)

        return QueryPlan(
            query_id       = req.query_id,
            steps          = steps,
            estimated_cost = total_cost,
            use_cache      = use_cache,
            cache_ttl      = cache_ttl,
            parallel       = parallel,
            optimized      = True,
            index_hint     = primary,
            notes          = notes,
        )

    def _index_for_lookup(
        self,
        target:         str,
        namespace_hint: Optional[str],
    ) -> IndexHint:
        """Choose the best index for a simple type lookup."""
        if target.startswith("iios.") or "." in target:
            # Looks like a URI → direct URI index
            return IndexHint.USE_URI_INDEX
        # Short names → might be an alias
        return IndexHint.USE_ALIAS_INDEX

    @staticmethod
    def _cost_for_index(hint: IndexHint) -> float:
        """Relative cost estimate per index type."""
        costs: dict[IndexHint, float] = {
            IndexHint.USE_URI_INDEX:       0.01,
            IndexHint.USE_ALIAS_INDEX:     0.05,
            IndexHint.USE_NAMESPACE_INDEX: 0.10,
            IndexHint.USE_LABEL_INDEX:     0.20,
            IndexHint.HIERARCHY_INDEX:     0.15,
            IndexHint.FULL_SCAN:           1.00,
        }
        return costs.get(hint, 1.0)

    @staticmethod
    def _ttl_for_type(qt: QueryType) -> float:
        """Cache TTL in seconds, by query type."""
        ttls: dict[QueryType, float] = {
            QueryType.TYPE_LOOKUP:    300.0,
            QueryType.HIERARCHY:      120.0,
            QueryType.ANCESTORS:      300.0,
            QueryType.DESCENDANTS:    120.0,
            QueryType.CHILDREN:       120.0,
            QueryType.PARENT:         300.0,
            QueryType.SEARCH:          60.0,
            QueryType.SEMANTIC:        60.0,
            QueryType.RELATIONSHIP_LOOKUP: 300.0,
            QueryType.METADATA:       300.0,
            QueryType.REFERENCE:       60.0,
            QueryType.CROSS_REFERENCE:  0.0,   # Never cache
            QueryType.NAMED:           60.0,
            QueryType.NEIGHBORHOOD:    60.0,
        }
        return ttls.get(qt, float(QUERY_CACHE_TTL_SECONDS))

    def stats(self) -> dict:
        avg = (self._total_ms / self._plan_count) if self._plan_count else 0.0
        return {
            "plan_count":   self._plan_count,
            "total_ms":     round(self._total_ms, 3),
            "avg_plan_ms":  round(avg, 3),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_opt_lock = threading.Lock()
_opt_instance: Optional[QueryOptimizer] = None


def get_query_optimizer() -> QueryOptimizer:
    global _opt_instance
    if _opt_instance is None:
        with _opt_lock:
            if _opt_instance is None:
                _opt_instance = QueryOptimizer()
    return _opt_instance


def reset_query_optimizer() -> None:
    global _opt_instance
    with _opt_lock:
        _opt_instance = None
