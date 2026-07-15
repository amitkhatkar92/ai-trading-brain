"""iios/investment/portfolio/risk/risk_health.py

Health monitoring for the Portfolio Risk Engine. Tracks run success/failure
and emits a health report.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RiskHealthReport:
    """Health status of the Portfolio Risk Engine."""

    report_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    is_healthy:          bool  = True
    total_runs:          int   = 0
    success_runs:        int   = 0
    failed_runs:         int   = 0
    success_rate:        float = 1.0
    avg_duration_ms:     float = 0.0
    last_duration_ms:    float = 0.0
    active_portfolios:   int   = 0
    error_message:       str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_healthy":        self.is_healthy,
            "total_runs":        self.total_runs,
            "success_runs":      self.success_runs,
            "failed_runs":       self.failed_runs,
            "success_rate":      round(self.success_rate, 4),
            "avg_duration_ms":   round(self.avg_duration_ms, 2),
            "active_portfolios": self.active_portfolios,
        }


class RiskHealthMonitor:
    """Thread-safe health monitor for the Risk Engine."""

    _MIN_SUCCESS_RATE = 0.70

    def __init__(self) -> None:
        self._lock      = threading.RLock()
        self._total     = 0
        self._succeeded = 0
        self._durations: List[float] = []
        self._last_dur  = 0.0

    def record_run(self, *, succeeded: bool, duration_ms: float) -> None:
        with self._lock:
            self._total += 1
            if succeeded:
                self._succeeded += 1
            self._durations.append(duration_ms)
            if len(self._durations) > 200:
                self._durations = self._durations[-200:]
            self._last_dur = duration_ms

    def check(self, *, active_portfolios: int = 0) -> RiskHealthReport:
        with self._lock:
            total    = self._total
            success  = self._succeeded
            failed   = total - success
            rate     = success / total if total else 1.0
            avg_dur  = sum(self._durations) / len(self._durations) if self._durations else 0.0
            healthy  = rate >= self._MIN_SUCCESS_RATE

            return RiskHealthReport(
                is_healthy        = healthy,
                total_runs        = total,
                success_runs      = success,
                failed_runs       = failed,
                success_rate      = round(rate, 4),
                avg_duration_ms   = round(avg_dur, 2),
                last_duration_ms  = round(self._last_dur, 2),
                active_portfolios = active_portfolios,
                error_message     = "" if healthy else f"Success rate {rate:.1%} below threshold",
            )
