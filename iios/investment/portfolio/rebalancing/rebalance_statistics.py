"""iios/investment/portfolio/rebalancing/rebalance_statistics.py

Run-level statistics for the Portfolio Rebalancing Engine.
"""
from __future__ import annotations

import statistics
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RebalanceRunMetric:
    """Per-run execution metric."""

    run_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:   str   = ""
    succeeded:      bool  = True
    duration_ms:    float = 0.0
    n_trades:       int   = 0
    rebalance_score:float = 0.0
    is_recommended: bool  = False


@dataclass(frozen=True)
class RebalanceStatisticsSnapshot:
    """Aggregated statistics over all runs."""

    total_runs:       int   = 0
    success_runs:     int   = 0
    failed_runs:      int   = 0
    success_rate:     float = 0.0
    avg_duration_ms:  float = 0.0
    p95_duration_ms:  float = 0.0
    avg_score:        float = 0.0
    best_score:       float = 0.0
    avg_n_trades:     float = 0.0
    recommended_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":      self.total_runs,
            "success_rate":    round(self.success_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "p95_duration_ms": round(self.p95_duration_ms, 2),
            "avg_score":       round(self.avg_score, 4),
            "recommended_rate":round(self.recommended_rate, 4),
        }


class PortfolioRebalanceStatistics:
    """Thread-safe bounded run statistics across all portfolios."""

    def __init__(self, max_runs: int = 1000) -> None:
        self._max   = max_runs
        self._lock  = threading.RLock()
        self._runs:  List[RebalanceRunMetric] = []

    def record(self, metric: RebalanceRunMetric) -> None:
        with self._lock:
            self._runs.append(metric)
            if len(self._runs) > self._max:
                self._runs = self._runs[-self._max:]

    def snapshot(self) -> RebalanceStatisticsSnapshot:
        with self._lock:
            if not self._runs:
                return RebalanceStatisticsSnapshot()
            n         = len(self._runs)
            successes = sum(1 for r in self._runs if r.succeeded)
            durations = sorted(r.duration_ms for r in self._runs)
            scores    = [r.rebalance_score for r in self._runs if r.succeeded]
            rec_rate  = sum(1 for r in self._runs if r.is_recommended) / n

            avg_dur   = sum(durations) / n
            p95_idx   = max(0, int(0.95 * n) - 1)
            p95_dur   = durations[p95_idx]

            avg_score = sum(scores) / len(scores) if scores else 0.0
            best_score= max(scores) if scores else 0.0
            avg_trades= sum(r.n_trades for r in self._runs) / n

            return RebalanceStatisticsSnapshot(
                total_runs       = n,
                success_runs     = successes,
                failed_runs      = n - successes,
                success_rate     = round(successes / n, 4),
                avg_duration_ms  = round(avg_dur, 2),
                p95_duration_ms  = round(p95_dur, 2),
                avg_score        = round(avg_score, 4),
                best_score       = round(best_score, 4),
                avg_n_trades     = round(avg_trades, 1),
                recommended_rate = round(rec_rate, 4),
            )
