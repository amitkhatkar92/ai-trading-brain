"""iios/execution/monitoring/integration/monitoring_integration_statistics.py
==================================================
IntegrationStatistics — mutable accumulator for integration subsystem
metrics.

Thread-safe via threading.RLock (to_dict() re-enters via derived properties).

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class IntegrationStatistics:
    """
    Mutable, thread-safe accumulator for integration runtime metrics.

    Fields
    ------
    requests_received:    Total submit() calls received.
    requests_completed:   Requests completed successfully.
    requests_failed:      Requests that resulted in an error.
    sessions_created:     Total monitoring sessions created.
    sessions_completed:   Sessions completed successfully.
    sessions_failed:      Sessions that transitioned to FAILED.
    snapshots_published:  Total integration snapshots published.
    alerts_generated:     Cumulative alerts generated across all cycles.
    metrics_cycles:       Total metrics evaluation cycles performed.
    validation_failures:  Total requests rejected at validation.
    health_checks:        Total health() calls.
    _total_duration_ms:   Cumulative evaluation duration for average.
    last_updated_at:      Wall-time of last write.
    """

    requests_received:   int   = 0
    requests_completed:  int   = 0
    requests_failed:     int   = 0
    sessions_created:    int   = 0
    sessions_completed:  int   = 0
    sessions_failed:     int   = 0
    snapshots_published: int   = 0
    alerts_generated:    int   = 0
    metrics_cycles:      int   = 0
    validation_failures: int   = 0
    health_checks:       int   = 0
    _total_duration_ms:  float = 0.0
    last_updated_at:     float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self._lock = threading.RLock()   # RLock: to_dict calls properties that re-enter

    # ── Write methods ─────────────────────────────────────────────────────────

    def record_request_received(self) -> None:
        with self._lock:
            self.requests_received += 1
            self.last_updated_at    = time.time()

    def record_request_completed(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self.requests_completed += 1
            self._total_duration_ms += duration_ms
            self.last_updated_at     = time.time()

    def record_request_failed(self) -> None:
        with self._lock:
            self.requests_failed  += 1
            self.last_updated_at   = time.time()

    def record_session_created(self) -> None:
        with self._lock:
            self.sessions_created += 1
            self.last_updated_at   = time.time()

    def record_session_completed(self) -> None:
        with self._lock:
            self.sessions_completed += 1
            self.last_updated_at     = time.time()

    def record_session_failed(self) -> None:
        with self._lock:
            self.sessions_failed  += 1
            self.last_updated_at   = time.time()

    def record_snapshot_published(self) -> None:
        with self._lock:
            self.snapshots_published += 1
            self.last_updated_at      = time.time()

    def record_alerts(self, count: int) -> None:
        with self._lock:
            self.alerts_generated += count
            self.last_updated_at   = time.time()

    def record_metrics_cycle(self) -> None:
        with self._lock:
            self.metrics_cycles  += 1
            self.last_updated_at  = time.time()

    def record_validation_failure(self) -> None:
        with self._lock:
            self.validation_failures += 1
            self.last_updated_at      = time.time()

    def record_health_check(self) -> None:
        with self._lock:
            self.health_checks    += 1
            self.last_updated_at   = time.time()

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def average_duration_ms(self) -> float:
        with self._lock:
            if self.requests_completed == 0:
                return 0.0
            return self._total_duration_ms / self.requests_completed

    @property
    def success_rate(self) -> float:
        with self._lock:
            total = self.requests_completed + self.requests_failed
            if total == 0:
                return 0.0
            return self.requests_completed / total

    @property
    def failure_rate(self) -> float:
        with self._lock:
            return 1.0 - self.success_rate

    # ── Utility ───────────────────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self.requests_received   = 0
            self.requests_completed  = 0
            self.requests_failed     = 0
            self.sessions_created    = 0
            self.sessions_completed  = 0
            self.sessions_failed     = 0
            self.snapshots_published = 0
            self.alerts_generated    = 0
            self.metrics_cycles      = 0
            self.validation_failures = 0
            self.health_checks       = 0
            self._total_duration_ms  = 0.0
            self.last_updated_at     = time.time()

    def copy(self) -> "IntegrationStatistics":
        with self._lock:
            s = IntegrationStatistics(
                requests_received   = self.requests_received,
                requests_completed  = self.requests_completed,
                requests_failed     = self.requests_failed,
                sessions_created    = self.sessions_created,
                sessions_completed  = self.sessions_completed,
                sessions_failed     = self.sessions_failed,
                snapshots_published = self.snapshots_published,
                alerts_generated    = self.alerts_generated,
                metrics_cycles      = self.metrics_cycles,
                validation_failures = self.validation_failures,
                health_checks       = self.health_checks,
                _total_duration_ms  = self._total_duration_ms,
                last_updated_at     = self.last_updated_at,
            )
            return s

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "requests_received":   self.requests_received,
                "requests_completed":  self.requests_completed,
                "requests_failed":     self.requests_failed,
                "sessions_created":    self.sessions_created,
                "sessions_completed":  self.sessions_completed,
                "sessions_failed":     self.sessions_failed,
                "snapshots_published": self.snapshots_published,
                "alerts_generated":    self.alerts_generated,
                "metrics_cycles":      self.metrics_cycles,
                "validation_failures": self.validation_failures,
                "health_checks":       self.health_checks,
                "average_duration_ms": self.average_duration_ms,
                "success_rate":        self.success_rate,
                "failure_rate":        self.failure_rate,
                "last_updated_at":     self.last_updated_at,
            }
