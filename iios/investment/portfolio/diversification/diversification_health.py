"""iios/investment/portfolio/diversification/diversification_health.py

Health monitoring for the PortfolioDiversificationEngine.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from iios.investment.portfolio.diversification.diversification_types import DiversificationStatus


@dataclass(frozen=True)
class DiversificationHealthCheck:
    check_id:   str                  = field(default_factory=lambda: str(uuid.uuid4()))
    check_name: str                  = ""
    status:     DiversificationStatus = DiversificationStatus.UNKNOWN
    message:    str                  = ""
    value:      float                = 0.0
    threshold:  float                = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":   self.check_id,
            "check_name": self.check_name,
            "status":     self.status.value,
            "message":    self.message,
            "value":      round(self.value, 4),
            "threshold":  round(self.threshold, 4),
        }


@dataclass(frozen=True)
class DiversificationHealthReport:
    report_id:          str                   = field(default_factory=lambda: str(uuid.uuid4()))
    overall_status:     DiversificationStatus = DiversificationStatus.UNKNOWN
    checks:             Tuple[DiversificationHealthCheck, ...] = field(default_factory=tuple)
    total_evaluations:  int                   = 0
    success_evaluations:int                   = 0
    failed_evaluations: int                   = 0
    error_rate:         float                 = 0.0
    avg_duration_ms:    float                 = 0.0
    active_portfolios:  int                   = 0
    uptime_seconds:     float                 = 0.0
    reported_at:        float                 = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == DiversificationStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":           self.report_id,
            "overall_status":      self.overall_status.value,
            "is_healthy":          self.is_healthy,
            "total_evaluations":   self.total_evaluations,
            "success_evaluations": self.success_evaluations,
            "failed_evaluations":  self.failed_evaluations,
            "error_rate":          round(self.error_rate, 4),
            "avg_duration_ms":     round(self.avg_duration_ms, 2),
            "active_portfolios":   self.active_portfolios,
            "uptime_seconds":      round(self.uptime_seconds, 1),
            "reported_at":         self.reported_at,
            "checks":              [c.to_dict() for c in self.checks],
        }


class DiversificationHealthMonitor:
    _ERROR_RATE_WARNING:  float = 0.20
    _ERROR_RATE_CRITICAL: float = 0.50
    _SLOW_P95:            float = 5_000.0

    def __init__(self, window: int = 100) -> None:
        self._window = window
        self._runs: List[Tuple[bool, float]] = []
        self._start = time.time()
        self._lock  = threading.Lock()

    def record_run(self, *, succeeded: bool, duration_ms: float) -> None:
        with self._lock:
            self._runs.append((succeeded, duration_ms))
            if len(self._runs) > self._window:
                self._runs.pop(0)

    def check(self, *, active_portfolios: int = 0) -> DiversificationHealthReport:
        with self._lock:
            runs = list(self._runs)

        total   = len(runs)
        success = sum(1 for s, _ in runs if s)
        failed  = total - success
        err_rt  = failed / total if total else 0.0
        avg_dur = sum(d for _, d in runs) / total if total else 0.0
        uptime  = time.time() - self._start
        durs    = sorted(d for _, d in runs)
        p95     = durs[int(len(durs) * 0.95)] if durs else 0.0

        checks = []

        if err_rt >= self._ERROR_RATE_CRITICAL:
            es = DiversificationStatus.FAILING
        elif err_rt >= self._ERROR_RATE_WARNING:
            es = DiversificationStatus.DEGRADED
        else:
            es = DiversificationStatus.HEALTHY
        checks.append(DiversificationHealthCheck(
            check_name = "error_rate",
            status     = es,
            message    = f"Error rate {err_rt:.1%} over {total} evaluation(s)",
            value      = err_rt,
            threshold  = self._ERROR_RATE_WARNING,
        ))

        ls = (DiversificationStatus.FAILING if p95 > self._SLOW_P95 * 2
              else DiversificationStatus.DEGRADED if p95 > self._SLOW_P95
              else DiversificationStatus.HEALTHY)
        checks.append(DiversificationHealthCheck(
            check_name = "p95_latency_ms",
            status     = ls,
            message    = f"P95 latency {p95:.0f} ms",
            value      = p95,
            threshold  = self._SLOW_P95,
        ))

        statuses = [c.status for c in checks]
        if DiversificationStatus.FAILING in statuses:
            overall = DiversificationStatus.FAILING
        elif DiversificationStatus.DEGRADED in statuses:
            overall = DiversificationStatus.DEGRADED
        elif all(s == DiversificationStatus.HEALTHY for s in statuses):
            overall = DiversificationStatus.HEALTHY
        else:
            overall = DiversificationStatus.UNKNOWN

        return DiversificationHealthReport(
            overall_status      = overall,
            checks              = tuple(checks),
            total_evaluations   = total,
            success_evaluations = success,
            failed_evaluations  = failed,
            error_rate          = err_rt,
            avg_duration_ms     = avg_dur,
            active_portfolios   = active_portfolios,
            uptime_seconds      = uptime,
        )
