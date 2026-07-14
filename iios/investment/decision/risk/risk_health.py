"""iios/investment/decision/risk/risk_health.py
RiskHealthMonitor — tracks engine health metrics across evaluations.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.risk.risk_constants import RiskEngineStatus


@dataclass(frozen=True)
class RiskHealthReport:
    status:              RiskEngineStatus
    total_evaluations:   int
    successful:          int
    failed:              int
    consecutive_failures: int
    avg_duration_ms:     float

    @property
    def is_healthy(self) -> bool:
        return (
            self.status in {RiskEngineStatus.READY, RiskEngineStatus.EVALUATING}
            and self.consecutive_failures < 5
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":               self.status.value,
            "total_evaluations":    self.total_evaluations,
            "successful":           self.successful,
            "failed":               self.failed,
            "consecutive_failures": self.consecutive_failures,
            "avg_duration_ms":      round(self.avg_duration_ms, 2),
            "is_healthy":           self.is_healthy,
        }


class RiskHealthMonitor:
    """Thread-safe engine health tracker."""

    def __init__(self) -> None:
        self._lock               = threading.RLock()
        self._status             = RiskEngineStatus.INITIALIZING
        self._total              = 0
        self._successful         = 0
        self._failed             = 0
        self._consecutive_fails  = 0
        self._duration_sum       = 0.0

    def set_status(self, status: RiskEngineStatus) -> None:
        with self._lock:
            self._status = status

    def record_success(self, duration_ms: float) -> None:
        with self._lock:
            self._total             += 1
            self._successful        += 1
            self._consecutive_fails  = 0
            self._duration_sum      += duration_ms

    def record_failure(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._total             += 1
            self._failed            += 1
            self._consecutive_fails += 1
            self._duration_sum      += duration_ms
            if self._consecutive_fails >= 5:
                self._status = RiskEngineStatus.DEGRADED

    def report(self) -> RiskHealthReport:
        with self._lock:
            avg_dur = self._duration_sum / max(1, self._total)
            return RiskHealthReport(
                status=self._status,
                total_evaluations=self._total,
                successful=self._successful,
                failed=self._failed,
                consecutive_failures=self._consecutive_fails,
                avg_duration_ms=round(avg_dur, 2),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = self._consecutive_fails = 0
            self._duration_sum = 0.0
            self._status = RiskEngineStatus.INITIALIZING
