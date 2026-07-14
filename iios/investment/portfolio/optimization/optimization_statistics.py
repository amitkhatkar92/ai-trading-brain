"""iios/investment/portfolio/optimization/optimization_statistics.py

Aggregated run-level statistics for the optimization engine.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class OptimizationRunMetric:
    """Single-run metric."""

    run_id:               str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str   = ""
    succeeded:            bool  = False
    positions_optimized:  int   = 0
    total_capital:        float = 0.0
    utilisation_rate:     float = 0.0
    objective_improvement:float = 0.0
    sharpe_proxy:         float = 0.0
    quality_score:        float = 0.0
    total_turnover:       float = 0.0
    duration_ms:          float = 0.0
    run_at:               float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":                self.run_id,
            "portfolio_id":          self.portfolio_id,
            "succeeded":             self.succeeded,
            "positions_optimized":   self.positions_optimized,
            "total_capital":         round(self.total_capital, 2),
            "utilisation_rate":      round(self.utilisation_rate, 4),
            "objective_improvement": round(self.objective_improvement, 6),
            "sharpe_proxy":          round(self.sharpe_proxy, 6),
            "quality_score":         round(self.quality_score, 4),
            "total_turnover":        round(self.total_turnover, 6),
            "duration_ms":           round(self.duration_ms, 2),
            "run_at":                self.run_at,
        }


@dataclass(frozen=True)
class OptimizationStatisticsSnapshot:
    """Point-in-time stats summary."""

    snapshot_id:                str   = field(default_factory=lambda: str(uuid.uuid4()))
    total_runs:                 int   = 0
    success_runs:               int   = 0
    failed_runs:                int   = 0
    success_rate:               float = 0.0
    avg_duration_ms:            float = 0.0
    p50_duration_ms:            float = 0.0
    p95_duration_ms:            float = 0.0
    avg_objective_improvement:  float = 0.0
    avg_quality_score:          float = 0.0
    avg_turnover:               float = 0.0
    portfolios_served:          int   = 0
    snapshotted_at:             float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":               self.snapshot_id,
            "total_runs":                self.total_runs,
            "success_runs":              self.success_runs,
            "failed_runs":               self.failed_runs,
            "success_rate":              round(self.success_rate, 4),
            "avg_duration_ms":           round(self.avg_duration_ms, 2),
            "p50_duration_ms":           round(self.p50_duration_ms, 2),
            "p95_duration_ms":           round(self.p95_duration_ms, 2),
            "avg_objective_improvement": round(self.avg_objective_improvement, 6),
            "avg_quality_score":         round(self.avg_quality_score, 4),
            "avg_turnover":              round(self.avg_turnover, 6),
            "portfolios_served":         self.portfolios_served,
            "snapshotted_at":            self.snapshotted_at,
        }


def _percentile(sorted_values: List[float], pct: int) -> float:
    if not sorted_values:
        return 0.0
    n   = len(sorted_values)
    idx = max(0, min(n - 1, int(pct / 100 * n)))
    return sorted_values[idx]


class OptimizationStatistics:
    """Thread-safe, bounded accumulator of optimization run metrics."""

    def __init__(self, max_runs: int = 1000) -> None:
        self._max_runs = max(1, max_runs)
        self._runs: List[OptimizationRunMetric] = []
        self._portfolios: set = set()
        self._lock  = threading.Lock()

    def record(self, metric: OptimizationRunMetric) -> None:
        with self._lock:
            self._runs.append(metric)
            if len(self._runs) > self._max_runs:
                self._runs.pop(0)
            if metric.portfolio_id:
                self._portfolios.add(metric.portfolio_id)

    def snapshot(self) -> OptimizationStatisticsSnapshot:
        with self._lock:
            runs = list(self._runs)
            n_pf = len(self._portfolios)

        total = len(runs)
        if total == 0:
            return OptimizationStatisticsSnapshot(portfolios_served=n_pf)

        success  = sum(1 for r in runs if r.succeeded)
        durs     = sorted(r.duration_ms for r in runs)
        obj_imp  = [r.objective_improvement for r in runs if r.succeeded]
        qualities= [r.quality_score for r in runs if r.succeeded and r.quality_score > 0]
        turnovers= [r.total_turnover for r in runs if r.succeeded]

        return OptimizationStatisticsSnapshot(
            total_runs                = total,
            success_runs              = success,
            failed_runs               = total - success,
            success_rate              = success / total,
            avg_duration_ms           = sum(durs) / len(durs),
            p50_duration_ms           = _percentile(durs, 50),
            p95_duration_ms           = _percentile(durs, 95),
            avg_objective_improvement = sum(obj_imp) / len(obj_imp) if obj_imp else 0.0,
            avg_quality_score         = sum(qualities) / len(qualities) if qualities else 0.0,
            avg_turnover              = sum(turnovers) / len(turnovers) if turnovers else 0.0,
            portfolios_served         = n_pf,
        )

    def for_portfolio(self, portfolio_id: str) -> "OptimizationStatistics":
        subset = OptimizationStatistics(max_runs=self._max_runs)
        with self._lock:
            for r in self._runs:
                if r.portfolio_id == portfolio_id:
                    subset._runs.append(r)
                    subset._portfolios.add(portfolio_id)
        return subset

    def recent(self, n: int = 20) -> Tuple[OptimizationRunMetric, ...]:
        with self._lock:
            return tuple(self._runs[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._runs)

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._portfolios)
