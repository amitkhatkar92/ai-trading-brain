"""iios/investment/portfolio/rebalancing/rebalance_health.py

Health monitor for the Portfolio Rebalancing Engine.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class RebalanceHealthReport:
    """Engine health snapshot."""

    report_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    is_healthy:        bool  = True
    total_runs:        int   = 0
    success_runs:      int   = 0
    failed_runs:       int   = 0
    success_rate:      float = 0.0
    avg_duration_ms:   float = 0.0
    active_portfolios: int   = 0
    plans_generated:   int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_healthy":       self.is_healthy,
            "total_runs":       self.total_runs,
            "success_rate":     round(self.success_rate, 4),
            "avg_duration_ms":  round(self.avg_duration_ms, 2),
            "active_portfolios":self.active_portfolios,
            "plans_generated":  self.plans_generated,
        }


class RebalanceHealthMonitor:
    """Thread-safe health accumulator for the rebalancing engine."""

    HEALTHY_MIN_SUCCESS_RATE = 0.80

    def __init__(self) -> None:
        self._lock          = threading.RLock()
        self._total         = 0
        self._successes     = 0
        self._failures      = 0
        self._total_dur_ms  = 0.0
        self._plans_gen     = 0

    def record_run(
        self,
        succeeded:    bool,
        duration_ms:  float = 0.0,
        plan_created: bool  = False,
    ) -> None:
        with self._lock:
            self._total        += 1
            self._total_dur_ms += duration_ms
            if succeeded:
                self._successes += 1
            else:
                self._failures  += 1
            if plan_created:
                self._plans_gen += 1

    def check(self, active_portfolios: int = 0) -> RebalanceHealthReport:
        with self._lock:
            if self._total == 0:
                return RebalanceHealthReport(active_portfolios=active_portfolios)
            sr = self._successes / self._total
            return RebalanceHealthReport(
                is_healthy        = sr >= self.HEALTHY_MIN_SUCCESS_RATE,
                total_runs        = self._total,
                success_runs      = self._successes,
                failed_runs       = self._failures,
                success_rate      = round(sr, 4),
                avg_duration_ms   = round(self._total_dur_ms / self._total, 2),
                active_portfolios = active_portfolios,
                plans_generated   = self._plans_gen,
            )
