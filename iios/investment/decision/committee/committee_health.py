"""iios/investment/decision/committee/committee_health.py
CommitteeHealthMonitor — tracks engine health across sessions.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.committee.committee_constants import CommitteeStatus


@dataclass(frozen=True)
class CommitteeHealthReport:
    status:               CommitteeStatus
    total_sessions:       int
    successful:           int
    failed:               int
    consecutive_failures: int
    avg_duration_ms:      float

    @property
    def is_healthy(self) -> bool:
        return (
            self.status in {CommitteeStatus.READY, CommitteeStatus.RUNNING}
            and self.consecutive_failures < 5
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":               self.status.value,
            "total_sessions":       self.total_sessions,
            "successful":           self.successful,
            "failed":               self.failed,
            "consecutive_failures": self.consecutive_failures,
            "avg_duration_ms":      round(self.avg_duration_ms, 2),
            "is_healthy":           self.is_healthy,
        }


class CommitteeHealthMonitor:
    """Thread-safe health tracker for the Committee Engine."""

    def __init__(self) -> None:
        self._lock         = threading.RLock()
        self._status       = CommitteeStatus.INITIALIZING
        self._total        = 0
        self._ok           = 0
        self._fail         = 0
        self._consec_fails = 0
        self._dur_sum      = 0.0

    def set_status(self, status: CommitteeStatus) -> None:
        with self._lock:
            self._status = status

    def record_success(self, duration_ms: float) -> None:
        with self._lock:
            self._total        += 1
            self._ok           += 1
            self._consec_fails  = 0
            self._dur_sum      += duration_ms

    def record_failure(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._total        += 1
            self._fail         += 1
            self._consec_fails += 1
            self._dur_sum      += duration_ms
            if self._consec_fails >= 5:
                self._status = CommitteeStatus.DEGRADED

    def report(self) -> CommitteeHealthReport:
        with self._lock:
            avg = self._dur_sum / max(1, self._total)
            return CommitteeHealthReport(
                status               = self._status,
                total_sessions       = self._total,
                successful           = self._ok,
                failed               = self._fail,
                consecutive_failures = self._consec_fails,
                avg_duration_ms      = round(avg, 2),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._ok = self._fail = self._consec_fails = 0
            self._dur_sum = 0.0
            self._status  = CommitteeStatus.INITIALIZING
