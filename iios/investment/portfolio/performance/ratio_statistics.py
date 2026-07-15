"""iios/investment/portfolio/performance/ratio_statistics.py

Statistics accumulator for performance ratios.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.performance.performance_ratios import PerformanceRatios


@dataclass(frozen=True)
class RatioStatisticsSnapshot:
    """Rolling statistics over multiple ratio runs."""

    n_runs:            int   = 0
    avg_sharpe:        float = 0.0
    avg_sortino:       float = 0.0
    avg_calmar:        float = 0.0
    avg_information_ratio: float = 0.0
    avg_omega:         float = 0.0
    pct_above_sharpe_1: float = 0.0   # % runs with Sharpe > 1
    best_sharpe:       float = 0.0
    worst_sharpe:      float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_runs":             self.n_runs,
            "avg_sharpe":         round(self.avg_sharpe, 4),
            "avg_sortino":        round(self.avg_sortino, 4),
            "avg_calmar":         round(self.avg_calmar, 4),
            "pct_above_sharpe_1": round(self.pct_above_sharpe_1, 4),
        }


class RatioStatistics:
    """Thread-safe rolling accumulator for performance ratios."""

    def __init__(self, max_runs: int = 500) -> None:
        self._max  = max_runs
        self._lock = threading.RLock()
        self._data: List[PerformanceRatios] = []

    def record(self, ratios: PerformanceRatios) -> None:
        with self._lock:
            self._data.append(ratios)
            if len(self._data) > self._max:
                self._data = self._data[-self._max:]

    def snapshot(self) -> RatioStatisticsSnapshot:
        with self._lock:
            if not self._data:
                return RatioStatisticsSnapshot()
            n = len(self._data)

            def _avg(attr):
                return sum(getattr(r, attr) for r in self._data) / n

            sharpes = [r.sharpe for r in self._data]
            above1  = sum(1 for s in sharpes if s > 1.0)

            return RatioStatisticsSnapshot(
                n_runs             = n,
                avg_sharpe         = round(_avg("sharpe"), 4),
                avg_sortino        = round(_avg("sortino"), 4),
                avg_calmar         = round(_avg("calmar"), 4),
                avg_information_ratio = round(_avg("information_ratio"), 4),
                avg_omega          = round(_avg("omega"), 4),
                pct_above_sharpe_1 = round(above1 / n, 4),
                best_sharpe        = round(max(sharpes), 4),
                worst_sharpe       = round(min(sharpes), 4),
            )
