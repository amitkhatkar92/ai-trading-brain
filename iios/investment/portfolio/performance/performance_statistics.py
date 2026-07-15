"""iios/investment/portfolio/performance/performance_statistics.py

Run statistics for the Portfolio Performance Engine.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class PerformanceRunMetric:
    """Metric captured per evaluation run."""

    run_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:     str   = ""
    succeeded:        bool  = True
    duration_ms:      float = 0.0
    n_positions:      int   = 0
    overall_score:    float = 0.0


@dataclass(frozen=True)
class PerformanceStatisticsSnapshot:
    """Aggregate statistics over many engine runs."""

    total_runs:       int   = 0
    success_runs:     int   = 0
    failed_runs:      int   = 0
    success_rate:     float = 0.0
    avg_duration_ms:  float = 0.0
    avg_score:        float = 0.0
    best_score:       float = 0.0
    worst_score:      float = 0.0
    n_portfolios:     int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":      self.total_runs,
            "success_rate":    round(self.success_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "avg_score":       round(self.avg_score, 4),
            "n_portfolios":    self.n_portfolios,
        }


class PortfolioPerformanceStatistics:
    """Thread-safe run statistics accumulator."""

    def __init__(self, max_runs: int = 1000) -> None:
        self._max  = max_runs
        self._lock = threading.RLock()
        self._data: List[PerformanceRunMetric] = []
        self._portfolios: set = set()

    def record(self, metric: PerformanceRunMetric) -> None:
        with self._lock:
            self._data.append(metric)
            self._portfolios.add(metric.portfolio_id)
            if len(self._data) > self._max:
                self._data = self._data[-self._max:]

    def snapshot(self) -> PerformanceStatisticsSnapshot:
        with self._lock:
            if not self._data:
                return PerformanceStatisticsSnapshot()
            n       = len(self._data)
            success = sum(1 for r in self._data if r.succeeded)
            total_dur = sum(r.duration_ms for r in self._data)
            scores  = [r.overall_score for r in self._data if r.succeeded]
            avg_score = sum(scores) / len(scores) if scores else 0.0

            return PerformanceStatisticsSnapshot(
                total_runs     = n,
                success_runs   = success,
                failed_runs    = n - success,
                success_rate   = round(success / n, 4),
                avg_duration_ms= round(total_dur / n, 2),
                avg_score      = round(avg_score, 4),
                best_score     = round(max(scores), 4) if scores else 0.0,
                worst_score    = round(min(scores), 4) if scores else 0.0,
                n_portfolios   = len(self._portfolios),
            )
