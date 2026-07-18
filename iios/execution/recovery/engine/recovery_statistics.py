"""
iios/execution/recovery/engine/recovery_statistics.py
=====================================================
Thread-safe statistics accumulator for the Execution Recovery Engine.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class RecoveryEngineStatistics:
    """
    Mutable, thread-safe statistics accumulator.

    All write methods are protected by an RLock.
    Derived properties (rates, averages) re-acquire the lock.
    """

    def __init__(self) -> None:
        self._lock             = threading.RLock()
        self.total_requests    = 0
        self.sessions_initiated = 0
        self.sessions_completed = 0   # successful completions
        self.sessions_failed    = 0
        self.sessions_cancelled = 0
        self.total_transitions  = 0
        self.total_verifications = 0
        self.successful_verifications = 0
        self._total_duration_ms  = 0.0
        self.last_updated_at     = time.time()

    # ── Write ─────────────────────────────────────────────────────────────────

    def record_request(self) -> None:
        with self._lock:
            self.total_requests += 1
            self.last_updated_at = time.time()

    def record_initiated(self) -> None:
        with self._lock:
            self.sessions_initiated += 1
            self.last_updated_at = time.time()

    def record_completed(self, duration_ms: float) -> None:
        with self._lock:
            self.sessions_completed += 1
            self._total_duration_ms += max(0.0, duration_ms)
            self.last_updated_at = time.time()

    def record_failed(self) -> None:
        with self._lock:
            self.sessions_failed += 1
            self.last_updated_at = time.time()

    def record_cancelled(self) -> None:
        with self._lock:
            self.sessions_cancelled += 1
            self.last_updated_at = time.time()

    def record_transition(self) -> None:
        with self._lock:
            self.total_transitions += 1
            self.last_updated_at = time.time()

    def record_verification(self, *, successful: bool) -> None:
        with self._lock:
            self.total_verifications += 1
            if successful:
                self.successful_verifications += 1
            self.last_updated_at = time.time()

    # ── Derived (read-only) ───────────────────────────────────────────────────

    @property
    def average_recovery_time_ms(self) -> float:
        with self._lock:
            if self.sessions_completed == 0:
                return 0.0
            return self._total_duration_ms / self.sessions_completed

    @property
    def success_rate(self) -> float:
        with self._lock:
            terminated = self.sessions_completed + self.sessions_failed + self.sessions_cancelled
            if terminated == 0:
                return 0.0
            return self.sessions_completed / terminated

    @property
    def failure_rate(self) -> float:
        with self._lock:
            terminated = self.sessions_completed + self.sessions_failed + self.sessions_cancelled
            if terminated == 0:
                return 0.0
            return self.sessions_failed / terminated

    @property
    def verification_success_rate(self) -> float:
        with self._lock:
            if self.total_verifications == 0:
                return 0.0
            return self.successful_verifications / self.total_verifications

    @property
    def subsystem_availability(self) -> float:
        """
        Estimated subsystem availability: fraction of initiated sessions that completed.
        Returns 0.0 if no sessions have been initiated.
        """
        with self._lock:
            if self.sessions_initiated == 0:
                return 0.0
            return self.sessions_completed / self.sessions_initiated

    # ── Management ────────────────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self.total_requests           = 0
            self.sessions_initiated       = 0
            self.sessions_completed       = 0
            self.sessions_failed          = 0
            self.sessions_cancelled       = 0
            self.total_transitions        = 0
            self.total_verifications      = 0
            self.successful_verifications = 0
            self._total_duration_ms       = 0.0
            self.last_updated_at          = time.time()

    def copy(self) -> "RecoveryEngineStatistics":
        """Return an independent snapshot of current statistics."""
        snap = RecoveryEngineStatistics()
        with self._lock:
            snap.total_requests           = self.total_requests
            snap.sessions_initiated       = self.sessions_initiated
            snap.sessions_completed       = self.sessions_completed
            snap.sessions_failed          = self.sessions_failed
            snap.sessions_cancelled       = self.sessions_cancelled
            snap.total_transitions        = self.total_transitions
            snap.total_verifications      = self.total_verifications
            snap.successful_verifications = self.successful_verifications
            snap._total_duration_ms       = self._total_duration_ms
            snap.last_updated_at          = self.last_updated_at
        return snap

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_requests":               self.total_requests,
                "sessions_initiated":           self.sessions_initiated,
                "sessions_completed":           self.sessions_completed,
                "sessions_failed":              self.sessions_failed,
                "sessions_cancelled":           self.sessions_cancelled,
                "total_transitions":            self.total_transitions,
                "total_verifications":          self.total_verifications,
                "successful_verifications":     self.successful_verifications,
                "average_recovery_time_ms":     self.average_recovery_time_ms,
                "success_rate":                 self.success_rate,
                "failure_rate":                 self.failure_rate,
                "verification_success_rate":    self.verification_success_rate,
                "subsystem_availability":       self.subsystem_availability,
                "last_updated_at":              self.last_updated_at,
            }
