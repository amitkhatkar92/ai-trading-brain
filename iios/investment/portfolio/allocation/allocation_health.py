"""iios/investment/portfolio/allocation/allocation_health.py

Health monitoring for the PortfolioAllocationEngine process.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


@dataclass(frozen=True)
class AllocationHealthCheck:
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
class AllocationHealthReport:
    """Full health report for the allocation engine."""

    report_id:        str          = field(default_factory=lambda: str(uuid.uuid4()))
    overall_status:   HealthStatus = HealthStatus.UNKNOWN
    checks:           Tuple[AllocationHealthCheck, ...] = field(default_factory=tuple)
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


class AllocationHealthMonitor:
    """
    Lightweight health tracker for the PortfolioAllocationEngine.
    Thread-safe. Maintains a rolling window of run outcomes.
    """

    _ERROR_RATE_THRESHOLD: float = 0.20    # Degraded if > 20 % errors
    _CRITICAL_ERROR_RATE:  float = 0.50    # Unhealthy if > 50 % errors
    _SLOW_P95_THRESHOLD:   float = 5000.0  # ms; degrade if P95 > 5 s

    def __init__(self, window: int = 100) -> None:
        self._window    = window
        self._runs:  List[Tuple[bool, float]] = []   # (succeeded, duration_ms)
        self._start  = time.time()
        self._lock   = threading.Lock()

    def record_run(self, *, succeeded: bool, duration_ms: float) -> None:
        with self._lock:
            self._runs.append((succeeded, duration_ms))
            if len(self._runs) > self._window:
                self._runs.pop(0)

    def check(self, *, active_portfolios: int = 0) -> AllocationHealthReport:
        with self._lock:
            runs = list(self._runs)

        total    = len(runs)
        success  = sum(1 for s, _ in runs if s)
        failed   = total - success
        err_rate = failed / total if total else 0.0
        avg_dur  = sum(d for _, d in runs) / total if total else 0.0
        uptime   = time.time() - self._start

        checks: List[AllocationHealthCheck] = []

        # -- Error rate ---
        if err_rate > self._CRITICAL_ERROR_RATE:
            er_status = HealthStatus.UNHEALTHY
        elif err_rate > self._ERROR_RATE_THRESHOLD:
            er_status = HealthStatus.DEGRADED
        else:
            er_status = HealthStatus.HEALTHY
        checks.append(AllocationHealthCheck(
            check_name = "error_rate",
            status     = er_status,
            message    = f"Error rate {err_rate:.1%} over last {total} run(s)",
            value      = err_rate,
            threshold  = self._ERROR_RATE_THRESHOLD,
        ))

        # -- Latency ---
        durations = sorted(d for _, d in runs)
        p95 = durations[int(len(durations) * 0.95)] if durations else 0.0
        lat_status = (
            HealthStatus.UNHEALTHY if p95 > self._SLOW_P95_THRESHOLD * 2
            else HealthStatus.DEGRADED if p95 > self._SLOW_P95_THRESHOLD
            else HealthStatus.HEALTHY
        )
        checks.append(AllocationHealthCheck(
            check_name = "p95_latency_ms",
            status     = lat_status,
            message    = f"P95 latency {p95:.0f} ms",
            value      = p95,
            threshold  = self._SLOW_P95_THRESHOLD,
        ))

        # -- Portfolio coverage ---
        pf_status = HealthStatus.HEALTHY if active_portfolios >= 0 else HealthStatus.UNKNOWN
        checks.append(AllocationHealthCheck(
            check_name = "active_portfolios",
            status     = pf_status,
            message    = f"{active_portfolios} portfolio(s) registered",
            value      = active_portfolios,
            threshold  = 0,
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

        return AllocationHealthReport(
            overall_status   = overall,
            checks           = tuple(checks),
            total_runs       = total,
            success_runs     = success,
            failed_runs      = failed,
            error_rate       = err_rate,
            avg_duration_ms  = avg_dur,
            active_portfolios= active_portfolios,
            uptime_seconds   = uptime,
        )
