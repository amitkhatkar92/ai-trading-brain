"""iios/investment/portfolio/optimization/optimization_health.py

Health monitoring for the PortfolioOptimizationEngine.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple


class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


@dataclass(frozen=True)
class OptimizationHealthCheck:
    """A single diagnostic check."""

    check_id:   str          = field(default_factory=lambda: str(uuid.uuid4()))
    check_name: str          = ""
    status:     HealthStatus = HealthStatus.UNKNOWN
    message:    str          = ""
    value:      float        = 0.0
    threshold:  float        = 0.0

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
class OptimizationHealthReport:
    """Full health report for the optimization engine."""

    report_id:        str          = field(default_factory=lambda: str(uuid.uuid4()))
    overall_status:   HealthStatus = HealthStatus.UNKNOWN
    checks:           Tuple[OptimizationHealthCheck, ...] = field(default_factory=tuple)
    total_runs:       int          = 0
    success_runs:     int          = 0
    failed_runs:      int          = 0
    error_rate:       float        = 0.0
    avg_duration_ms:  float        = 0.0
    active_portfolios:int          = 0
    uptime_seconds:   float        = 0.0
    reported_at:      float        = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":         self.report_id,
            "overall_status":    self.overall_status.value,
            "is_healthy":        self.is_healthy,
            "total_runs":        self.total_runs,
            "success_runs":      self.success_runs,
            "failed_runs":       self.failed_runs,
            "error_rate":        round(self.error_rate, 4),
            "avg_duration_ms":   round(self.avg_duration_ms, 2),
            "active_portfolios": self.active_portfolios,
            "uptime_seconds":    round(self.uptime_seconds, 1),
            "reported_at":       self.reported_at,
            "checks":            [c.to_dict() for c in self.checks],
        }


class OptimizationHealthMonitor:
    """Thread-safe health tracker for the PortfolioOptimizationEngine."""

    _ERROR_RATE_THRESHOLD: float = 0.20
    _CRITICAL_ERROR_RATE:  float = 0.50
    _SLOW_P95_THRESHOLD:   float = 10_000.0   # ms

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

    def check(self, *, active_portfolios: int = 0) -> OptimizationHealthReport:
        with self._lock:
            runs = list(self._runs)

        total   = len(runs)
        success = sum(1 for s, _ in runs if s)
        failed  = total - success
        err_rt  = failed / total if total else 0.0
        avg_dur = sum(d for _, d in runs) / total if total else 0.0
        uptime  = time.time() - self._start

        checks: List[OptimizationHealthCheck] = []

        # Error rate
        if err_rt > self._CRITICAL_ERROR_RATE:
            es = HealthStatus.UNHEALTHY
        elif err_rt > self._ERROR_RATE_THRESHOLD:
            es = HealthStatus.DEGRADED
        else:
            es = HealthStatus.HEALTHY
        checks.append(OptimizationHealthCheck(
            check_name = "error_rate",
            status     = es,
            message    = f"Error rate {err_rt:.1%} over {total} run(s)",
            value      = err_rt,
            threshold  = self._ERROR_RATE_THRESHOLD,
        ))

        # P95 latency
        durs = sorted(d for _, d in runs)
        p95  = durs[int(len(durs) * 0.95)] if durs else 0.0
        ls   = (HealthStatus.UNHEALTHY if p95 > self._SLOW_P95_THRESHOLD * 2
                else HealthStatus.DEGRADED if p95 > self._SLOW_P95_THRESHOLD
                else HealthStatus.HEALTHY)
        checks.append(OptimizationHealthCheck(
            check_name = "p95_latency_ms",
            status     = ls,
            message    = f"P95 latency {p95:.0f} ms",
            value      = p95,
            threshold  = self._SLOW_P95_THRESHOLD,
        ))

        checks.append(OptimizationHealthCheck(
            check_name = "active_portfolios",
            status     = HealthStatus.HEALTHY,
            message    = f"{active_portfolios} portfolio(s) registered",
            value      = active_portfolios,
        ))

        statuses = [c.status for c in checks]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        return OptimizationHealthReport(
            overall_status    = overall,
            checks            = tuple(checks),
            total_runs        = total,
            success_runs      = success,
            failed_runs       = failed,
            error_rate        = err_rt,
            avg_duration_ms   = avg_dur,
            active_portfolios = active_portfolios,
            uptime_seconds    = uptime,
        )
