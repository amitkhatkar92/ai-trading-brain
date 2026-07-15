"""iios/investment/portfolio/risk/stress_statistics.py

Aggregate statistics across multiple stress test runs.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.risk.stress_testing import StressTestReport


@dataclass(frozen=True)
class StressRunMetric:
    """Lightweight record of a single stress test run."""

    run_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str   = ""
    n_scenarios_run: int   = 0
    worst_loss:      float = 0.0
    avg_loss:        float = 0.0
    resilience_score:float = 1.0
    tail_avg_loss:   float = 0.0


@dataclass(frozen=True)
class StressStatisticsSnapshot:
    """Aggregate statistics over recent stress test runs."""

    total_runs:          int   = 0
    avg_resilience:      float = 1.0
    min_resilience:      float = 1.0
    avg_worst_loss:      float = 0.0
    avg_tail_loss:       float = 0.0
    deterioration_runs:  int   = 0   # resilience < 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":         self.total_runs,
            "avg_resilience":     round(self.avg_resilience, 4),
            "min_resilience":     round(self.min_resilience, 4),
            "avg_worst_loss":     round(self.avg_worst_loss, 4),
            "avg_tail_loss":      round(self.avg_tail_loss, 4),
            "deterioration_runs": self.deterioration_runs,
        }


class StressStatistics:
    """Thread-safe accumulator for stress test run statistics."""

    def __init__(self, max_runs: int = 200) -> None:
        self._max   = max_runs
        self._lock  = threading.RLock()
        self._runs: List[StressRunMetric] = []

    def record(self, report: StressTestReport) -> None:
        with self._lock:
            m = StressRunMetric(
                portfolio_id    = report.portfolio_id,
                n_scenarios_run = report.n_scenarios_run,
                worst_loss      = report.worst_loss,
                avg_loss        = report.avg_loss,
                resilience_score= report.resilience_score,
                tail_avg_loss   = report.tail_avg_loss,
            )
            self._runs.append(m)
            if len(self._runs) > self._max:
                self._runs = self._runs[-self._max:]

    def snapshot(self) -> StressStatisticsSnapshot:
        with self._lock:
            if not self._runs:
                return StressStatisticsSnapshot()
            n    = len(self._runs)
            resil = [r.resilience_score for r in self._runs]
            worst = [r.worst_loss for r in self._runs]
            tail  = [r.tail_avg_loss for r in self._runs]
            detrn = sum(1 for r in resil if r < 0.5)
            return StressStatisticsSnapshot(
                total_runs       = n,
                avg_resilience   = round(sum(resil) / n, 4),
                min_resilience   = round(min(resil), 4),
                avg_worst_loss   = round(sum(worst) / n, 4),
                avg_tail_loss    = round(sum(tail) / n, 4),
                deterioration_runs= detrn,
            )
