"""
cost_tracker.py -- iios.ai.foundation.cost
============================================
CostTracker -- thread-safe accumulator for AI execution costs.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from .cost_models import CostSummary, ExecutionCost, TokenUsage


class CostTracker:
    """
    Thread-safe in-memory cost accumulator.

    Records :class:`ExecutionCost` entries, provides per-session
    summaries, and supports budget enforcement.

    Designed to be injected per-session or per-pipeline run.
    """

    def __init__(self, session_id: str = "", budget_usd: float = 0.0) -> None:
        self._session_id   = session_id
        self._budget_usd   = budget_usd
        self._lock         = threading.Lock()
        self._records:     List[ExecutionCost] = []
        self._start:       float               = time.time()

    # ---- recording --------------------------------------------------------

    def record(self, cost: ExecutionCost) -> None:
        """Record one execution cost entry."""
        with self._lock:
            self._records.append(cost)

    # ---- queries ----------------------------------------------------------

    def total_tokens(self) -> int:
        with self._lock:
            return sum(r.token_usage.total_tokens for r in self._records)

    def total_cost_usd(self) -> float:
        with self._lock:
            return sum(r.total_cost_usd for r in self._records)

    def execution_count(self) -> int:
        with self._lock:
            return len(self._records)

    def is_over_budget(self) -> bool:
        """Return True iff a non-zero budget is set and exceeded."""
        if self._budget_usd <= 0:
            return False
        return self.total_cost_usd() > self._budget_usd

    def budget_remaining(self) -> Optional[float]:
        """Remaining budget, or None if no budget is set."""
        if self._budget_usd <= 0:
            return None
        return max(0.0, self._budget_usd - self.total_cost_usd())

    def summary(self) -> CostSummary:
        """Return an immutable cost summary for all recorded executions."""
        now = time.time()
        with self._lock:
            records = list(self._records)
        total    = sum(r.total_cost_usd for r in records)
        tokens   = sum(r.token_usage.total_tokens for r in records)
        count    = len(records)
        by_prov: Dict[str, float] = {}
        for r in records:
            by_prov[r.provider_id] = by_prov.get(r.provider_id, 0.0) + r.total_cost_usd
        return CostSummary(
            period_id       = self._session_id or "unnamed",
            execution_count = count,
            total_tokens    = tokens,
            total_cost_usd  = total,
            avg_cost_usd    = (total / count) if count else 0.0,
            period_start    = self._start,
            period_end      = now,
            by_provider     = by_prov,
        )

    def records(self) -> List[ExecutionCost]:
        with self._lock:
            return list(self._records)

    def __repr__(self) -> str:
        return (
            f"<CostTracker session={self._session_id!r} "
            f"executions={self.execution_count()} "
            f"total_usd={self.total_cost_usd():.4f}>"
        )
