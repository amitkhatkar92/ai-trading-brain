"""iios/investment/portfolio/risk/portfolio_risk_statistics.py

Thread-safe run statistics for the Portfolio Risk Engine.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RiskRunMetric:
    """Metadata for a single PortfolioRiskEngine.evaluate() call."""

    run_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str   = ""
    succeeded:       bool  = True
    duration_ms:     float = 0.0
    overall_score:   float = 0.0
    is_acceptable:   bool  = True
    n_alerts:        int   = 0


@dataclass(frozen=True)
class RiskStatisticsSnapshot:
    """Aggregate statistics over recent engine runs."""

    total_runs:          int   = 0
    success_runs:        int   = 0
    failed_runs:         int   = 0
    success_rate:        float = 1.0
    avg_duration_ms:     float = 0.0
    avg_risk_score:      float = 0.0
    acceptable_runs:     int   = 0
    acceptable_rate:     float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":      self.total_runs,
            "success_runs":    self.success_runs,
            "failed_runs":     self.failed_runs,
            "success_rate":    round(self.success_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "avg_risk_score":  round(self.avg_risk_score, 4),
            "acceptable_rate": round(self.acceptable_rate, 4),
        }


class PortfolioRiskStatistics:
    """Thread-safe accumulator for Portfolio Risk Engine run statistics."""

    def __init__(self, max_runs: int = 1000) -> None:
        self._max   = max_runs
        self._lock  = threading.RLock()
        self._runs: List[RiskRunMetric] = []

    def record(
        self,
        *,
        portfolio_id:  str,
        succeeded:     bool,
        duration_ms:   float,
        overall_score: float,
        is_acceptable: bool,
        n_alerts:      int,
    ) -> None:
        with self._lock:
            m = RiskRunMetric(
                portfolio_id  = portfolio_id,
                succeeded     = succeeded,
                duration_ms   = duration_ms,
                overall_score = overall_score,
                is_acceptable = is_acceptable,
                n_alerts      = n_alerts,
            )
            self._runs.append(m)
            if len(self._runs) > self._max:
                self._runs = self._runs[-self._max:]

    def snapshot(self) -> RiskStatisticsSnapshot:
        with self._lock:
            if not self._runs:
                return RiskStatisticsSnapshot()
            n       = len(self._runs)
            success = sum(1 for r in self._runs if r.succeeded)
            accept  = sum(1 for r in self._runs if r.is_acceptable)
            avg_dur = sum(r.duration_ms for r in self._runs) / n
            avg_scr = sum(r.overall_score for r in self._runs) / n
            return RiskStatisticsSnapshot(
                total_runs       = n,
                success_runs     = success,
                failed_runs      = n - success,
                success_rate     = round(success / n, 4),
                avg_duration_ms  = round(avg_dur, 2),
                avg_risk_score   = round(avg_scr, 4),
                acceptable_runs  = accept,
                acceptable_rate  = round(accept / n, 4),
            )
