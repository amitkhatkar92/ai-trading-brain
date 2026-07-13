"""iios/investment/strategy/lifecycle/performance_tracker.py
Execution performance metrics — computed from ExecutionTracker records.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.strategy.lifecycle.execution_tracker import (
    ExecutionRecord,
    ExecutionStatus,
    ExecutionTracker,
)


@dataclass
class PerformanceMetrics:
    """Statistical performance summary for a strategy or the whole engine."""

    strategy_id: Optional[str]  # None means global
    sample_count: int
    success_count: int
    failure_count: int
    timeout_count: int
    success_rate: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    computed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def failure_rate(self) -> float:
        if self.sample_count == 0:
            return 0.0
        return self.failure_count / self.sample_count

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "sample_count": self.sample_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "timeout_count": self.timeout_count,
            "success_rate": round(self.success_rate, 4),
            "failure_rate": round(self.failure_rate, 4),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "mean_ms": round(self.mean_ms, 2),
            "computed_at": self.computed_at.isoformat(),
        }


class PerformanceTracker:
    """
    Computes performance metrics from ExecutionTracker records on demand.

    No caching — always computed from live records to reflect the current
    window of execution history.
    """

    def __init__(self, execution_tracker: ExecutionTracker) -> None:
        self._tracker = execution_tracker

    def compute(
        self,
        strategy_id: Optional[str] = None,
        last_n: int = 200,
    ) -> PerformanceMetrics:
        """
        Compute performance metrics for a strategy or globally.

        Args:
            strategy_id: Scope to this strategy; None = global.
            last_n: Number of recent records to include.
        """
        if strategy_id:
            records = self._tracker.get_for_strategy(strategy_id, last_n)
        else:
            records = self._tracker.get_recent(last_n)

        completed = [r for r in records if r.is_complete]
        durations = [r.duration_ms for r in completed if r.duration_ms > 0]

        success = sum(1 for r in completed if r.succeeded)
        failed = sum(
            1 for r in completed if r.status == ExecutionStatus.FAILED
        )
        timed_out = sum(
            1 for r in completed if r.status == ExecutionStatus.TIMEOUT
        )
        n = len(completed)

        return PerformanceMetrics(
            strategy_id=strategy_id,
            sample_count=n,
            success_count=success,
            failure_count=failed,
            timeout_count=timed_out,
            success_rate=success / n if n > 0 else 1.0,
            p50_ms=self._pct(durations, 50),
            p95_ms=self._pct(durations, 95),
            p99_ms=self._pct(durations, 99),
            min_ms=min(durations) if durations else 0.0,
            max_ms=max(durations) if durations else 0.0,
            mean_ms=sum(durations) / len(durations) if durations else 0.0,
        )

    def all_strategy_metrics(
        self, last_n: int = 100
    ) -> Dict[str, PerformanceMetrics]:
        """Compute metrics for every strategy seen in the tracker."""
        strategy_ids = self._tracker.known_strategy_ids()
        return {
            sid: self.compute(strategy_id=sid, last_n=last_n)
            for sid in strategy_ids
        }

    @staticmethod
    def _pct(values: List[float], pct: int) -> float:
        if not values:
            return 0.0
        sorted_v = sorted(values)
        idx = max(0, math.ceil(len(sorted_v) * pct / 100) - 1)
        return sorted_v[idx]
