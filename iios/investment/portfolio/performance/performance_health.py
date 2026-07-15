"""iios/investment/portfolio/performance/performance_health.py

Health monitor for the Portfolio Performance Engine.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class PerformanceHealthReport:
    """Snapshot of engine health."""

    report_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    is_healthy:        bool  = True
    total_runs:        int   = 0
    success_runs:      int   = 0
    failed_runs:       int   = 0
    success_rate:      float = 0.0
    avg_duration_ms:   float = 0.0
    active_portfolios: int   = 0
    uptime_pct:        float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_healthy":       self.is_healthy,
            "total_runs":       self.total_runs,
            "success_rate":     round(self.success_rate, 4),
            "avg_duration_ms":  round(self.avg_duration_ms, 2),
            "active_portfolios":self.active_portfolios,
        }


class PerformanceHealthMonitor:
    """Thread-safe accumulator for engine health metrics."""

    HEALTHY_MIN_SUCCESS_RATE = 0.80

    def __init__(self) -> None:
        self._lock         = threading.RLock()
        self._total        = 0
        self._successes    = 0
        self._failures     = 0
        self._total_dur_ms = 0.0

    def record_run(self, succeeded: bool, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._total        += 1
            self._total_dur_ms += duration_ms
            if succeeded:
                self._successes += 1
            else:
                self._failures  += 1

    def check(self, active_portfolios: int = 0) -> PerformanceHealthReport:
        with self._lock:
            n = self._total
            if n == 0:
                return PerformanceHealthReport(
                    active_portfolios = active_portfolios,
                )
            sr = self._successes / n
            avg_dur = self._total_dur_ms / n
            healthy = sr >= self.HEALTHY_MIN_SUCCESS_RATE

            return PerformanceHealthReport(
                is_healthy        = healthy,
                total_runs        = n,
                success_runs      = self._successes,
                failed_runs       = self._failures,
                success_rate      = round(sr, 4),
                avg_duration_ms   = round(avg_dur, 2),
                active_portfolios = active_portfolios,
                uptime_pct        = round(sr * 100, 2),
            )
