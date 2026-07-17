"""iios/execution/monitoring/lifecycle/monitoring_statistics.py
==================================================
MonitoringStatistics — mutable accumulator for monitoring lifecycle metrics.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MonitoringStatistics:
    """Mutable accumulator for lifecycle-wide monitoring metrics."""

    sessions_created:  int   = 0
    sessions_started:  int   = 0
    sessions_paused:   int   = 0
    sessions_resumed:  int   = 0
    sessions_stopped:  int   = 0
    sessions_failed:   int   = 0
    sessions_archived: int   = 0
    total_transitions: int   = 0
    total_duration_ms: float = 0.0
    last_updated_at:   float = 0.0

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    # ── Record helpers ────────────────────────────────────────────────────────

    def record_created(self) -> None:
        with self._lock:
            self.sessions_created += 1
            self.last_updated_at   = time.time()

    def record_started(self) -> None:
        with self._lock:
            self.sessions_started += 1
            self.last_updated_at   = time.time()

    def record_paused(self) -> None:
        with self._lock:
            self.sessions_paused += 1
            self.last_updated_at  = time.time()

    def record_resumed(self) -> None:
        with self._lock:
            self.sessions_resumed += 1
            self.last_updated_at  = time.time()

    def record_stopped(self, duration_ms: Optional[float] = None) -> None:
        with self._lock:
            self.sessions_stopped  += 1
            if duration_ms is not None:
                self.total_duration_ms += duration_ms
            self.last_updated_at = time.time()

    def record_failed(self) -> None:
        with self._lock:
            self.sessions_failed += 1
            self.last_updated_at  = time.time()

    def record_archived(self) -> None:
        with self._lock:
            self.sessions_archived += 1
            self.last_updated_at   = time.time()

    def record_transition(self) -> None:
        with self._lock:
            self.total_transitions += 1
            self.last_updated_at    = time.time()

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def sessions_completed(self) -> int:
        return self.sessions_stopped + self.sessions_failed

    @property
    def average_session_duration_ms(self) -> float:
        if self.sessions_stopped == 0:
            return 0.0
        return self.total_duration_ms / self.sessions_stopped

    @property
    def success_rate(self) -> float:
        total = self.sessions_completed
        if total == 0:
            return 0.0
        return self.sessions_stopped / total

    @property
    def failure_rate(self) -> float:
        total = self.sessions_completed
        if total == 0:
            return 0.0
        return self.sessions_failed / total

    # ── Utilities ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self.sessions_created  = 0
            self.sessions_started  = 0
            self.sessions_paused   = 0
            self.sessions_resumed  = 0
            self.sessions_stopped  = 0
            self.sessions_failed   = 0
            self.sessions_archived = 0
            self.total_transitions = 0
            self.total_duration_ms = 0.0
            self.last_updated_at   = 0.0

    def copy(self) -> "MonitoringStatistics":
        with self._lock:
            s = MonitoringStatistics(
                sessions_created  = self.sessions_created,
                sessions_started  = self.sessions_started,
                sessions_paused   = self.sessions_paused,
                sessions_resumed  = self.sessions_resumed,
                sessions_stopped  = self.sessions_stopped,
                sessions_failed   = self.sessions_failed,
                sessions_archived = self.sessions_archived,
                total_transitions = self.total_transitions,
                total_duration_ms = self.total_duration_ms,
                last_updated_at   = self.last_updated_at,
            )
        return s

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sessions_created":           self.sessions_created,
                "sessions_started":           self.sessions_started,
                "sessions_paused":            self.sessions_paused,
                "sessions_resumed":           self.sessions_resumed,
                "sessions_stopped":           self.sessions_stopped,
                "sessions_failed":            self.sessions_failed,
                "sessions_archived":          self.sessions_archived,
                "total_transitions":          self.total_transitions,
                "total_duration_ms":          self.total_duration_ms,
                "average_session_duration_ms":self.average_session_duration_ms,
                "success_rate":               self.success_rate,
                "failure_rate":               self.failure_rate,
                "last_updated_at":            self.last_updated_at,
            }
