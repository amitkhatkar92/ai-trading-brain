"""
iios/execution/recovery/integration/recovery_integration_statistics.py
======================================================================
IntegrationStatistics — thread-safe statistics for the Integration subsystem.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict


class IntegrationStatistics:
    """
    Thread-safe, in-memory statistics for the Integration subsystem.

    Tracks request counts, recovery outcomes, snapshot publication counts,
    and timing averages.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._total_requests:       int   = 0
        self._total_sessions:       int   = 0
        self._successful:           int   = 0
        self._failed:               int   = 0
        self._snapshots_published:  int   = 0
        self._response_count:       int   = 0
        self._total_response_ms:    float = 0.0
        self._recovery_count:       int   = 0
        self._total_recovery_ms:    float = 0.0

    # ── Mutating ──────────────────────────────────────────────────────────────

    def record_request(self) -> None:
        with self._lock:
            self._total_requests += 1

    def record_session(self) -> None:
        with self._lock:
            self._total_sessions += 1

    def record_success(self) -> None:
        with self._lock:
            self._successful += 1

    def record_failure(self) -> None:
        with self._lock:
            self._failed += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots_published += 1

    def record_response_time(self, ms: float) -> None:
        with self._lock:
            self._response_count += 1
            self._total_response_ms += ms

    def record_recovery_time(self, ms: float) -> None:
        with self._lock:
            self._recovery_count += 1
            self._total_recovery_ms += ms

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def total_requests(self) -> int:
        with self._lock:
            return self._total_requests

    @property
    def total_sessions(self) -> int:
        with self._lock:
            return self._total_sessions

    @property
    def successful_recoveries(self) -> int:
        with self._lock:
            return self._successful

    @property
    def failed_recoveries(self) -> int:
        with self._lock:
            return self._failed

    @property
    def snapshots_published(self) -> int:
        with self._lock:
            return self._snapshots_published

    @property
    def success_rate(self) -> float:
        with self._lock:
            total = self._successful + self._failed
            if total == 0:
                return 0.0
            return self._successful / total

    @property
    def average_response_time_ms(self) -> float:
        with self._lock:
            if self._response_count == 0:
                return 0.0
            return self._total_response_ms / self._response_count

    @property
    def average_recovery_time_ms(self) -> float:
        with self._lock:
            if self._recovery_count == 0:
                return 0.0
            return self._total_recovery_ms / self._recovery_count

    # ── Copy / reset ──────────────────────────────────────────────────────────

    def copy(self) -> "IntegrationStatistics":
        with self._lock:
            other = IntegrationStatistics()
            other._total_requests      = self._total_requests
            other._total_sessions      = self._total_sessions
            other._successful          = self._successful
            other._failed              = self._failed
            other._snapshots_published = self._snapshots_published
            other._response_count      = self._response_count
            other._total_response_ms   = self._total_response_ms
            other._recovery_count      = self._recovery_count
            other._total_recovery_ms   = self._total_recovery_ms
        return other

    def reset(self) -> None:
        with self._lock:
            self._total_requests      = 0
            self._total_sessions      = 0
            self._successful          = 0
            self._failed              = 0
            self._snapshots_published = 0
            self._response_count      = 0
            self._total_response_ms   = 0.0
            self._recovery_count      = 0
            self._total_recovery_ms   = 0.0

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_requests":          self._total_requests,
                "total_sessions":          self._total_sessions,
                "successful_recoveries":   self._successful,
                "failed_recoveries":       self._failed,
                "snapshots_published":     self._snapshots_published,
                "success_rate":            self.success_rate,
                "average_response_time_ms": self.average_response_time_ms,
                "average_recovery_time_ms": self.average_recovery_time_ms,
            }
