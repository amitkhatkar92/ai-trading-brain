"""iios/investment/portfolio/integration/portfolio_statistics.py

Run-level statistics for the Portfolio Intelligence Integration Engine.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass(frozen=True)
class IntegrationRunMetric:
    run_id:             str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str   = ""
    succeeded:          bool  = True
    duration_ms:        float = 0.0
    n_engines:          int   = 0
    completeness:       float = 0.0
    consistency_score:  float = 0.0
    quality_score:      float = 0.0
    n_conflicts:        int   = 0
    snapshot_published: bool  = False


@dataclass(frozen=True)
class PortfolioIntegrationStatisticsSnapshot:
    total_runs:           int   = 0
    success_runs:         int   = 0
    failed_runs:          int   = 0
    success_rate:         float = 0.0
    avg_duration_ms:      float = 0.0
    avg_completeness:     float = 0.0
    avg_quality_score:    float = 0.0
    avg_n_conflicts:      float = 0.0
    n_portfolios_tracked: int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":          self.total_runs,
            "success_rate":        round(self.success_rate, 4),
            "avg_duration_ms":     round(self.avg_duration_ms, 2),
            "avg_quality_score":   round(self.avg_quality_score, 4),
            "avg_completeness":    round(self.avg_completeness, 4),
            "avg_n_conflicts":     round(self.avg_n_conflicts, 2),
            "n_portfolios_tracked": self.n_portfolios_tracked,
        }


class PortfolioIntegrationStatistics:
    """Thread-safe run-level statistics accumulator."""

    def __init__(self, max_runs: int = 500) -> None:
        self._max         = max_runs
        self._lock        = threading.RLock()
        self._runs:       List[IntegrationRunMetric] = []
        self._portfolios: Set[str]                   = set()

    def record(self, metric: IntegrationRunMetric) -> None:
        with self._lock:
            self._runs.append(metric)
            self._portfolios.add(metric.portfolio_id)
            if len(self._runs) > self._max:
                self._runs = self._runs[-self._max:]

    def snapshot(self) -> PortfolioIntegrationStatisticsSnapshot:
        with self._lock:
            n_port = len(self._portfolios)
            if not self._runs:
                return PortfolioIntegrationStatisticsSnapshot(
                    n_portfolios_tracked=n_port,
                )
            n         = len(self._runs)
            successes = sum(1 for r in self._runs if r.succeeded)
            return PortfolioIntegrationStatisticsSnapshot(
                total_runs           = n,
                success_runs         = successes,
                failed_runs          = n - successes,
                success_rate         = successes / n,
                avg_duration_ms      = sum(r.duration_ms    for r in self._runs) / n,
                avg_completeness     = sum(r.completeness   for r in self._runs) / n,
                avg_quality_score    = sum(r.quality_score  for r in self._runs) / n,
                avg_n_conflicts      = sum(r.n_conflicts     for r in self._runs) / n,
                n_portfolios_tracked = n_port,
            )
