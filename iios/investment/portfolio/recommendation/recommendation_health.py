"""iios/investment/portfolio/recommendation/recommendation_health.py

Engine health monitor for the Portfolio Recommendation Engine.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class RecommendationHealthReport:
    """Snapshot of the recommendation engine's health."""

    report_id:              str   = field(default_factory=lambda: str(uuid.uuid4()))
    is_healthy:             bool  = True
    total_runs:             int   = 0
    success_runs:           int   = 0
    failed_runs:            int   = 0
    success_rate:           float = 0.0
    avg_duration_ms:        float = 0.0
    active_portfolios:      int   = 0
    recommendations_issued: int   = 0

    HEALTHY_MIN_SUCCESS_RATE: float = 0.80

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_healthy":             self.is_healthy,
            "total_runs":             self.total_runs,
            "success_rate":           round(self.success_rate, 4),
            "avg_duration_ms":        round(self.avg_duration_ms, 2),
            "active_portfolios":      self.active_portfolios,
            "recommendations_issued": self.recommendations_issued,
        }


class RecommendationHealthMonitor:
    """Thread-safe health accumulator for the recommendation engine."""

    HEALTHY_MIN_SUCCESS_RATE = 0.80

    def __init__(self) -> None:
        self._lock            = threading.RLock()
        self._total           = 0
        self._successes       = 0
        self._failures        = 0
        self._total_dur_ms    = 0.0
        self._recs_issued     = 0

    def record_run(
        self,
        succeeded:    bool,
        duration_ms:  float = 0.0,
        n_recs:       int   = 0,
    ) -> None:
        with self._lock:
            self._total        += 1
            self._total_dur_ms += duration_ms
            if succeeded:
                self._successes += 1
            else:
                self._failures  += 1
            self._recs_issued  += n_recs

    def check(self, active_portfolios: int = 0) -> RecommendationHealthReport:
        with self._lock:
            if self._total == 0:
                return RecommendationHealthReport(active_portfolios=active_portfolios)
            sr = self._successes / self._total
            return RecommendationHealthReport(
                is_healthy              = sr >= self.HEALTHY_MIN_SUCCESS_RATE,
                total_runs              = self._total,
                success_runs            = self._successes,
                failed_runs             = self._failures,
                success_rate            = round(sr, 4),
                avg_duration_ms         = round(self._total_dur_ms / self._total, 2),
                active_portfolios       = active_portfolios,
                recommendations_issued  = self._recs_issued,
            )
