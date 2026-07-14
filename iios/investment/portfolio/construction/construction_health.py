"""iios/investment/portfolio/construction/construction_health.py

Operational health monitoring for the construction engine and
individual portfolios.  Health is derived from recent run metrics —
it does NOT recompute portfolio quality.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import HealthStatus


# ---------------------------------------------------------------------------
# HealthCheckResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a single health check probe."""

    check_id:    str          = field(default_factory=lambda: str(uuid.uuid4()))
    check_name:  str          = ""
    status:      HealthStatus = HealthStatus.UNKNOWN
    message:     str          = ""
    value:       float        = 0.0
    threshold:   float        = 0.0
    checked_at:  float        = field(default_factory=time.time)
    details:     Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":   self.check_id,
            "check_name": self.check_name,
            "status":     self.status.value,
            "message":    self.message,
            "value":      round(self.value, 4),
            "threshold":  self.threshold,
            "checked_at": self.checked_at,
            "details":    dict(self.details),
        }


# ---------------------------------------------------------------------------
# EngineHealthReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineHealthReport:
    """Aggregate health report for the PortfolioConstructionEngine."""

    report_id:       str                         = field(default_factory=lambda: str(uuid.uuid4()))
    overall_status:  HealthStatus                = HealthStatus.UNKNOWN
    checks:          Tuple[HealthCheckResult, ...] = field(default_factory=tuple)
    total_runs:      int                         = 0
    error_count:     int                         = 0
    error_rate:      float                       = 0.0
    avg_duration_ms: float                       = 0.0
    active_portfolios: int                       = 0
    uptime_seconds:  float                       = 0.0
    generated_at:    float                       = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":         self.report_id,
            "overall_status":    self.overall_status.value,
            "total_runs":        self.total_runs,
            "error_count":       self.error_count,
            "error_rate":        round(self.error_rate, 4),
            "avg_duration_ms":   round(self.avg_duration_ms, 2),
            "active_portfolios": self.active_portfolios,
            "uptime_seconds":    round(self.uptime_seconds, 1),
            "checks":            [c.to_dict() for c in self.checks],
            "generated_at":      self.generated_at,
        }


# ---------------------------------------------------------------------------
# ConstructionHealthMonitor
# ---------------------------------------------------------------------------

class ConstructionHealthMonitor:
    """
    Monitors PortfolioConstructionEngine operational health by tracking
    run metrics, error rates, and latency.

    Not a separate thread — call check() on demand.
    """

    # Thresholds
    _MAX_ERROR_RATE   = 0.20   # 20% error rate = UNHEALTHY
    _WARN_ERROR_RATE  = 0.10   # 10% = DEGRADED
    _MAX_AVG_LATENCY  = 5000.0 # ms
    _WARN_AVG_LATENCY = 2000.0 # ms

    def __init__(self) -> None:
        self._lock            = threading.Lock()
        self._run_count       = 0
        self._error_count     = 0
        self._durations: List[float] = []   # last 100 run durations
        self._started_at      = time.time()

    # ------------------------------------------------------------------
    # Record a run outcome
    # ------------------------------------------------------------------

    def record_run(self, *, success: bool, duration_ms: float) -> None:
        with self._lock:
            self._run_count += 1
            if not success:
                self._error_count += 1
            self._durations.append(duration_ms)
            if len(self._durations) > 100:
                self._durations.pop(0)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def check(self, *, active_portfolios: int = 0) -> EngineHealthReport:
        with self._lock:
            total   = self._run_count
            errors  = self._error_count
            durs    = list(self._durations)

        err_rate = errors / total if total > 0 else 0.0
        avg_dur  = sum(durs) / len(durs) if durs else 0.0
        uptime   = time.time() - self._started_at

        checks: List[HealthCheckResult] = [
            self._check_error_rate(err_rate),
            self._check_latency(avg_dur),
            self._check_has_runs(total),
        ]

        # Overall = worst of all individual checks
        statuses = [c.status for c in checks]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return EngineHealthReport(
            overall_status    = overall,
            checks            = tuple(checks),
            total_runs        = total,
            error_count       = errors,
            error_rate        = round(err_rate, 4),
            avg_duration_ms   = round(avg_dur, 2),
            active_portfolios = active_portfolios,
            uptime_seconds    = round(uptime, 1),
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_error_rate(self, rate: float) -> HealthCheckResult:
        if rate >= self._MAX_ERROR_RATE:
            status, msg = HealthStatus.UNHEALTHY, f"Error rate {rate:.1%} exceeds {self._MAX_ERROR_RATE:.0%}"
        elif rate >= self._WARN_ERROR_RATE:
            status, msg = HealthStatus.DEGRADED, f"Error rate {rate:.1%} is elevated"
        else:
            status, msg = HealthStatus.HEALTHY, f"Error rate {rate:.1%} is acceptable"
        return HealthCheckResult(
            check_name="error_rate", status=status, message=msg,
            value=rate, threshold=self._MAX_ERROR_RATE,
        )

    def _check_latency(self, avg_ms: float) -> HealthCheckResult:
        if avg_ms >= self._MAX_AVG_LATENCY:
            status, msg = HealthStatus.UNHEALTHY, f"Avg latency {avg_ms:.0f}ms exceeds limit"
        elif avg_ms >= self._WARN_AVG_LATENCY:
            status, msg = HealthStatus.DEGRADED, f"Avg latency {avg_ms:.0f}ms is elevated"
        else:
            status, msg = HealthStatus.HEALTHY, f"Avg latency {avg_ms:.0f}ms is normal"
        return HealthCheckResult(
            check_name="avg_latency_ms", status=status, message=msg,
            value=avg_ms, threshold=self._MAX_AVG_LATENCY,
        )

    def _check_has_runs(self, total: int) -> HealthCheckResult:
        if total == 0:
            return HealthCheckResult(
                check_name="has_runs", status=HealthStatus.UNKNOWN,
                message="No construction runs yet", value=0.0, threshold=1.0,
            )
        return HealthCheckResult(
            check_name="has_runs", status=HealthStatus.HEALTHY,
            message=f"{total} construction run(s) recorded", value=float(total), threshold=1.0,
        )
