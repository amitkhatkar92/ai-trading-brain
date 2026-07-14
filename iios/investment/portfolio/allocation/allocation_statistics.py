"""iios/investment/portfolio/allocation/allocation_statistics.py

Aggregated run-level statistics for the allocation engine.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AllocationRunMetric:
    """Single-run metric stored in AllocationStatistics."""

    run_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:     str   = ""
    succeeded:        bool  = False
    positions_out:    int   = 0
    total_capital:    float = 0.0
    utilisation_rate: float = 0.0
    quality_score:    float = 0.0
    duration_ms:      float = 0.0
    run_at:           float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":           self.run_id,
            "portfolio_id":     self.portfolio_id,
            "succeeded":        self.succeeded,
            "positions_out":    self.positions_out,
            "total_capital":    round(self.total_capital, 2),
            "utilisation_rate": round(self.utilisation_rate, 4),
            "quality_score":    round(self.quality_score, 4),
            "duration_ms":      round(self.duration_ms, 2),
            "run_at":           self.run_at,
        }


@dataclass(frozen=True)
class AllocationStatisticsSnapshot:
    """Point-in-time statistics summary."""

    snapshot_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    total_runs:           int   = 0
    success_runs:         int   = 0
    failed_runs:          int   = 0
    success_rate:         float = 0.0
    avg_duration_ms:      float = 0.0
    p50_duration_ms:      float = 0.0
    p95_duration_ms:      float = 0.0
    avg_utilisation_rate: float = 0.0
    avg_quality_score:    float = 0.0
    avg_positions_out:    float = 0.0
    portfolios_served:    int   = 0
    total_capital_allocated: float = 0.0
    snapshotted_at:       float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":           self.snapshot_id,
            "total_runs":            self.total_runs,
            "success_runs":          self.success_runs,
            "failed_runs":           self.failed_runs,
            "success_rate":          round(self.success_rate, 4),
            "avg_duration_ms":       round(self.avg_duration_ms, 2),
            "p50_duration_ms":       round(self.p50_duration_ms, 2),
            "p95_duration_ms":       round(self.p95_duration_ms, 2),
            "avg_utilisation_rate":  round(self.avg_utilisation_rate, 4),
            "avg_quality_score":     round(self.avg_quality_score, 4),
            "avg_positions_out":     round(self.avg_positions_out, 2),
            "portfolios_served":     self.portfolios_served,
            "total_capital_allocated": round(self.total_capital_allocated, 2),
            "snapshotted_at":        self.snapshotted_at,
        }


class AllocationStatistics:
    """Thread-safe, bounded accumulator of allocation run metrics."""

    __slots__ = ("_max_runs", "_runs", "_portfolios", "_lock")

    def __init__(self, max_runs: int = 1000) -> None:
        self._max_runs    = max(1, max_runs)
        self._runs: List[AllocationRunMetric] = []
        self._portfolios: set = set()
        self._lock        = threading.Lock()

    def record(self, metric: AllocationRunMetric) -> None:
        with self._lock:
            self._runs.append(metric)
            if len(self._runs) > self._max_runs:
                self._runs.pop(0)
            if metric.portfolio_id:
                self._portfolios.add(metric.portfolio_id)

    def snapshot(self) -> AllocationStatisticsSnapshot:
        with self._lock:
            runs    = list(self._runs)
            n_pf    = len(self._portfolios)

        total = len(runs)
        if total == 0:
            return AllocationStatisticsSnapshot(portfolios_served=n_pf)

        success_runs = sum(1 for r in runs if r.succeeded)
        durations    = sorted(r.duration_ms for r in runs)
        utils        = [r.utilisation_rate for r in runs if r.succeeded]
        qualities    = [r.quality_score for r in runs if r.succeeded and r.quality_score > 0]
        positions    = [r.positions_out for r in runs if r.succeeded]
        capital      = sum(r.total_capital for r in runs if r.succeeded)

        return AllocationStatisticsSnapshot(
            total_runs               = total,
            success_runs             = success_runs,
            failed_runs              = total - success_runs,
            success_rate             = success_runs / total,
            avg_duration_ms          = sum(durations) / len(durations),
            p50_duration_ms          = _percentile(durations, 50),
            p95_duration_ms          = _percentile(durations, 95),
            avg_utilisation_rate     = sum(utils) / len(utils) if utils else 0.0,
            avg_quality_score        = sum(qualities) / len(qualities) if qualities else 0.0,
            avg_positions_out        = sum(positions) / len(positions) if positions else 0.0,
            portfolios_served        = n_pf,
            total_capital_allocated  = capital,
        )

    def for_portfolio(self, portfolio_id: str) -> "AllocationStatistics":
        subset = AllocationStatistics(max_runs=self._max_runs)
        with self._lock:
            for r in self._runs:
                if r.portfolio_id == portfolio_id:
                    subset._runs.append(r)
                    subset._portfolios.add(portfolio_id)
        return subset

    def recent(self, n: int = 20) -> Tuple[AllocationRunMetric, ...]:
        with self._lock:
            return tuple(self._runs[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._runs)

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._portfolios)


def _percentile(sorted_values: List[float], pct: int) -> float:
    if not sorted_values:
        return 0.0
    n   = len(sorted_values)
    idx = max(0, min(n - 1, int(pct / 100 * n)))
    return sorted_values[idx]
