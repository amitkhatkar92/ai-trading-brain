"""
integration_statistics.py — iios.integration.lifecycle
-------------------------------------------------------
Thread-safe statistics for the Integration Lifecycle module.

6 metrics:
  1. integration_sessions_created
  2. integration_sessions_completed
  3. integration_sessions_failed
  4. integration_sessions_archived
  5. transition_count
  6. average_session_duration_ms  (computed from durations)

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class IntegrationLifecycleStatisticsReport:
    """Point-in-time statistics snapshot for the lifecycle system."""
    integration_sessions_created:   int
    integration_sessions_completed: int
    integration_sessions_failed:    int
    integration_sessions_archived:  int
    transition_count:               int
    average_session_duration_ms:    float
    captured_at:                    str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_sessions_created":   self.integration_sessions_created,
            "integration_sessions_completed": self.integration_sessions_completed,
            "integration_sessions_failed":    self.integration_sessions_failed,
            "integration_sessions_archived":  self.integration_sessions_archived,
            "transition_count":               self.transition_count,
            "average_session_duration_ms":    self.average_session_duration_ms,
            "captured_at":                    self.captured_at,
        }


class IntegrationLifecycleStatistics:
    """Thread-safe rolling statistics for the lifecycle system."""

    def __init__(self) -> None:
        self._lock                           = threading.Lock()
        self._sessions_created               = 0
        self._sessions_completed             = 0
        self._sessions_failed                = 0
        self._sessions_archived              = 0
        self._transition_count               = 0
        self._total_duration_ms              = 0.0
        self._completed_with_duration_count  = 0

    # ----------------------------------------------------------------
    # Increment
    # ----------------------------------------------------------------

    def record_created(self) -> None:
        with self._lock:
            self._sessions_created += 1

    def record_completed(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._sessions_completed += 1
            if duration_ms > 0:
                self._total_duration_ms             += duration_ms
                self._completed_with_duration_count += 1

    def record_failed(self) -> None:
        with self._lock:
            self._sessions_failed += 1

    def record_archived(self) -> None:
        with self._lock:
            self._sessions_archived += 1

    def record_transition(self) -> None:
        with self._lock:
            self._transition_count += 1

    # ----------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------

    def report(self) -> IntegrationLifecycleStatisticsReport:
        with self._lock:
            avg = (
                self._total_duration_ms / self._completed_with_duration_count
                if self._completed_with_duration_count > 0 else 0.0
            )
            return IntegrationLifecycleStatisticsReport(
                integration_sessions_created   = self._sessions_created,
                integration_sessions_completed = self._sessions_completed,
                integration_sessions_failed    = self._sessions_failed,
                integration_sessions_archived  = self._sessions_archived,
                transition_count               = self._transition_count,
                average_session_duration_ms    = round(avg, 3),
                captured_at                    = datetime.now(tz=timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._sessions_created              = 0
            self._sessions_completed            = 0
            self._sessions_failed               = 0
            self._sessions_archived             = 0
            self._transition_count              = 0
            self._total_duration_ms             = 0.0
            self._completed_with_duration_count = 0
