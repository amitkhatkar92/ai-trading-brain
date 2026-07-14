"""iios/investment/decision/explainability/explainability_health.py
ExplainabilityHealthMonitor — tracks engine health across generation runs.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.explainability.explainability_constants import ExplainabilityStatus


@dataclass(frozen=True)
class ExplainabilityHealthReport:
    status:               ExplainabilityStatus
    total_generations:    int
    successful:           int
    failed:               int
    consecutive_failures: int
    avg_duration_ms:      float

    @property
    def is_healthy(self) -> bool:
        return (
            self.status in {ExplainabilityStatus.READY, ExplainabilityStatus.GENERATING}
            and self.consecutive_failures < 5
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":               self.status.value,
            "total_generations":    self.total_generations,
            "successful":           self.successful,
            "failed":               self.failed,
            "consecutive_failures": self.consecutive_failures,
            "avg_duration_ms":      round(self.avg_duration_ms, 2),
            "is_healthy":           self.is_healthy,
        }


class ExplainabilityHealthMonitor:
    """Thread-safe health tracker for the Explainability Engine."""

    def __init__(self) -> None:
        self._lock             = threading.RLock()
        self._status           = ExplainabilityStatus.INITIALIZING
        self._total            = 0
        self._successful       = 0
        self._failed           = 0
        self._consec_fails     = 0
        self._duration_sum     = 0.0

    def set_status(self, status: ExplainabilityStatus) -> None:
        with self._lock:
            self._status = status

    def record_success(self, duration_ms: float) -> None:
        with self._lock:
            self._total         += 1
            self._successful    += 1
            self._consec_fails   = 0
            self._duration_sum  += duration_ms

    def record_failure(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._total         += 1
            self._failed        += 1
            self._consec_fails  += 1
            self._duration_sum  += duration_ms
            if self._consec_fails >= 5:
                self._status = ExplainabilityStatus.DEGRADED

    def report(self) -> ExplainabilityHealthReport:
        with self._lock:
            avg = self._duration_sum / max(1, self._total)
            return ExplainabilityHealthReport(
                status               = self._status,
                total_generations    = self._total,
                successful           = self._successful,
                failed               = self._failed,
                consecutive_failures = self._consec_fails,
                avg_duration_ms      = round(avg, 2),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = self._consec_fails = 0
            self._duration_sum = 0.0
            self._status = ExplainabilityStatus.INITIALIZING
