"""
model_health.py -- iios.ai.model_management.health
====================================================
:class:`ModelHealth` — mutable, per-model health tracker.

Failure threshold for UNAVAILABLE transition: 3 consecutive failures.
One success resets to AVAILABLE.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import time
import threading
from typing import Optional

from .availability_status import AvailabilityStatus
from .health_report        import HealthReport

# Consecutive failures required to transition AVAILABLE → UNAVAILABLE
_FAILURE_THRESHOLD = 3


class ModelHealth:
    """Mutable, thread-safe per-model health state machine."""

    def __init__(self, model_id: str) -> None:
        self._model_id:       str                     = model_id
        self._status:         AvailabilityStatus      = AvailabilityStatus.UNKNOWN
        self._failure_count:  int                     = 0
        self._recovery_count: int                     = 0
        self._consecutive_failures: int               = 0
        self._last_check_at:  Optional[float]         = None
        self._last_failure_at: Optional[float]        = None
        self._lock:           threading.RLock         = threading.RLock()

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def status(self) -> AvailabilityStatus:
        with self._lock:
            return self._status

    # ── State transitions ─────────────────────────────────────────────────────

    def record_success(self) -> bool:
        """Record a successful health check.  Returns True if status changed."""
        with self._lock:
            self._consecutive_failures = 0
            self._last_check_at        = time.time()
            changed = self._status != AvailabilityStatus.AVAILABLE
            if changed:
                self._recovery_count += 1
            self._status = AvailabilityStatus.AVAILABLE
            return changed

    def record_failure(self) -> bool:
        """Record a failed health check.  Returns True if status changed."""
        with self._lock:
            self._failure_count        += 1
            self._consecutive_failures += 1
            self._last_check_at         = time.time()
            self._last_failure_at       = time.time()

            old_status = self._status
            if self._consecutive_failures >= _FAILURE_THRESHOLD:
                self._status = AvailabilityStatus.UNAVAILABLE
            elif self._status == AvailabilityStatus.AVAILABLE:
                self._status = AvailabilityStatus.DEGRADED
            return self._status != old_status

    def force_available(self) -> None:
        with self._lock:
            self._status = AvailabilityStatus.AVAILABLE
            self._consecutive_failures = 0

    def force_unavailable(self) -> None:
        with self._lock:
            self._status = AvailabilityStatus.UNAVAILABLE

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def to_report(self) -> HealthReport:
        with self._lock:
            return HealthReport(
                model_id        = self._model_id,
                status          = self._status,
                failure_count   = self._failure_count,
                recovery_count  = self._recovery_count,
                last_check_at   = self._last_check_at,
                last_failure_at = self._last_failure_at,
            )
