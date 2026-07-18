"""iios/execution/recovery/lifecycle/recovery_statistics.py
==================================================
RecoveryStatistics — mutable, thread-safe accumulator for recovery
lifecycle runtime metrics.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RecoveryStatistics:
    """
    Mutable thread-safe accumulator for recovery lifecycle counters.

    Thread safety via threading.RLock — derived properties (completion_rate,
    failure_rate, average_duration_ms) re-enter the lock via to_dict().
    """

    sessions_created:    int   = 0
    sessions_completed:  int   = 0
    sessions_failed:     int   = 0
    sessions_aborted:    int   = 0
    sessions_archived:   int   = 0
    total_transitions:   int   = 0
    _total_duration_ms:  float = 0.0
    last_updated_at:     float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self._lock = threading.RLock()   # RLock: derived properties re-enter

    # ── Write methods ─────────────────────────────────────────────────────────

    def record_created(self) -> None:
        with self._lock:
            self.sessions_created += 1
            self.last_updated_at   = time.time()

    def record_completed(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self.sessions_completed += 1
            self._total_duration_ms += duration_ms
            self.last_updated_at     = time.time()

    def record_failed(self) -> None:
        with self._lock:
            self.sessions_failed += 1
            self.last_updated_at  = time.time()

    def record_aborted(self) -> None:
        with self._lock:
            self.sessions_aborted += 1
            self.last_updated_at   = time.time()

    def record_archived(self) -> None:
        with self._lock:
            self.sessions_archived += 1
            self.last_updated_at    = time.time()

    def record_transition(self) -> None:
        with self._lock:
            self.total_transitions += 1
            self.last_updated_at    = time.time()

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def average_duration_ms(self) -> float:
        with self._lock:
            if self.sessions_completed == 0:
                return 0.0
            return self._total_duration_ms / self.sessions_completed

    @property
    def completion_rate(self) -> float:
        """Fraction of terminated sessions that completed successfully."""
        with self._lock:
            terminated = self.sessions_completed + self.sessions_failed + self.sessions_aborted
            if terminated == 0:
                return 0.0
            return self.sessions_completed / terminated

    @property
    def failure_rate(self) -> float:
        with self._lock:
            terminated = self.sessions_completed + self.sessions_failed + self.sessions_aborted
            if terminated == 0:
                return 0.0
            return self.sessions_failed / terminated

    @property
    def abort_rate(self) -> float:
        with self._lock:
            terminated = self.sessions_completed + self.sessions_failed + self.sessions_aborted
            if terminated == 0:
                return 0.0
            return self.sessions_aborted / terminated

    # ── Utility ───────────────────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self.sessions_created    = 0
            self.sessions_completed  = 0
            self.sessions_failed     = 0
            self.sessions_aborted    = 0
            self.sessions_archived   = 0
            self.total_transitions   = 0
            self._total_duration_ms  = 0.0
            self.last_updated_at     = time.time()

    def copy(self) -> "RecoveryStatistics":
        with self._lock:
            s = RecoveryStatistics(
                sessions_created   = self.sessions_created,
                sessions_completed = self.sessions_completed,
                sessions_failed    = self.sessions_failed,
                sessions_aborted   = self.sessions_aborted,
                sessions_archived  = self.sessions_archived,
                total_transitions  = self.total_transitions,
                _total_duration_ms = self._total_duration_ms,
                last_updated_at    = self.last_updated_at,
            )
            return s

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sessions_created":   self.sessions_created,
                "sessions_completed": self.sessions_completed,
                "sessions_failed":    self.sessions_failed,
                "sessions_aborted":   self.sessions_aborted,
                "sessions_archived":  self.sessions_archived,
                "total_transitions":  self.total_transitions,
                "average_duration_ms":self.average_duration_ms,
                "completion_rate":    self.completion_rate,
                "failure_rate":       self.failure_rate,
                "abort_rate":         self.abort_rate,
                "last_updated_at":    self.last_updated_at,
            }
