"""
iios/execution/analytics/lifecycle/analytics_statistics.py
==========================================================
AnalyticsStatistics — thread-safe statistics for the Analytics Lifecycle.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Any, Dict


class AnalyticsStatistics:
    """
    Thread-safe, in-memory statistics for the Analytics Lifecycle.

    Tracks session counts, outcomes, and timing averages.
    """

    def __init__(self) -> None:
        self._lock                       = threading.RLock()
        self._sessions_created:    int   = 0
        self._sessions_completed:  int   = 0
        self._sessions_failed:     int   = 0
        self._sessions_archived:   int   = 0
        self._transition_count:    int   = 0
        self._duration_count:      int   = 0
        self._total_duration_s:    float = 0.0

    # ── Mutating ──────────────────────────────────────────────────────────────

    def record_created(self) -> None:
        with self._lock:
            self._sessions_created += 1

    def record_completed(self, duration_seconds: float = 0.0) -> None:
        with self._lock:
            self._sessions_completed += 1
            if duration_seconds > 0.0:
                self._duration_count  += 1
                self._total_duration_s += duration_seconds

    def record_failed(self) -> None:
        with self._lock:
            self._sessions_failed += 1

    def record_archived(self) -> None:
        with self._lock:
            self._sessions_archived += 1

    def record_transition(self) -> None:
        with self._lock:
            self._transition_count += 1

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def sessions_created(self) -> int:
        with self._lock:
            return self._sessions_created

    @property
    def sessions_completed(self) -> int:
        with self._lock:
            return self._sessions_completed

    @property
    def sessions_failed(self) -> int:
        with self._lock:
            return self._sessions_failed

    @property
    def sessions_archived(self) -> int:
        with self._lock:
            return self._sessions_archived

    @property
    def transition_count(self) -> int:
        with self._lock:
            return self._transition_count

    @property
    def average_session_duration_seconds(self) -> float:
        with self._lock:
            if self._duration_count == 0:
                return 0.0
            return self._total_duration_s / self._duration_count

    @property
    def success_rate(self) -> float:
        with self._lock:
            resolved = self._sessions_completed + self._sessions_failed
            if resolved == 0:
                return 0.0
            return self._sessions_completed / resolved

    # ── Copy / reset ──────────────────────────────────────────────────────────

    def copy(self) -> "AnalyticsStatistics":
        with self._lock:
            other = AnalyticsStatistics()
            other._sessions_created   = self._sessions_created
            other._sessions_completed = self._sessions_completed
            other._sessions_failed    = self._sessions_failed
            other._sessions_archived  = self._sessions_archived
            other._transition_count   = self._transition_count
            other._duration_count     = self._duration_count
            other._total_duration_s   = self._total_duration_s
        return other

    def reset(self) -> None:
        with self._lock:
            self._sessions_created    = 0
            self._sessions_completed  = 0
            self._sessions_failed     = 0
            self._sessions_archived   = 0
            self._transition_count    = 0
            self._duration_count      = 0
            self._total_duration_s    = 0.0

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sessions_created":              self._sessions_created,
                "sessions_completed":            self._sessions_completed,
                "sessions_failed":               self._sessions_failed,
                "sessions_archived":             self._sessions_archived,
                "transition_count":              self._transition_count,
                "average_session_duration_s":    self.average_session_duration_seconds,
                "success_rate":                  self.success_rate,
            }
