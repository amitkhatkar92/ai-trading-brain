"""
analytics_integration_statistics.py — iios.execution.analytics.integration
===========================================================================
Thread-safe mutable statistics container for the Execution Analytics
Integration subsystem.

Tracks the seven counters / rates mandated by the specification.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class AnalyticsIntegrationStatistics:
    """
    Thread-safe statistics for the analytics integration subsystem.

    The seven tracked metrics are:

    1. **Analytics Requests**         — total requests received.
    2. **Analytics Sessions**         — total M1 analytics sessions created.
    3. **Analytics Snapshots Published** — total M5 snapshots published.
    4. **Performance Reports Generated** — total M3 reports produced.
    5. **Forecasts Generated**        — total M4 prediction reports produced.
    6. **Subsystem Availability**     — rolling availability ratio (0.0-1.0).
    7. **Average Response Time (ms)** — rolling average processing latency.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # counters
        self._requests:            int   = 0
        self._sessions:            int   = 0
        self._snapshots_published: int   = 0
        self._performance_reports: int   = 0
        self._forecasts:           int   = 0
        self._failed_requests:     int   = 0
        self._rejected_requests:   int   = 0

        # rolling latency (exponential moving average, α=0.1)
        self._avg_response_ms: float = 0.0
        self._ema_alpha:       float = 0.1

        # availability tracking (uptime ticks vs total ticks)
        self._uptime_ticks: int = 0
        self._total_ticks:  int = 0

        self._created_at: float = time.time()

    # ------------------------------------------------------------------
    # Mutators (call from manager)
    # ------------------------------------------------------------------
    def record_request_received(self) -> None:
        with self._lock:
            self._requests += 1

    def record_session_created(self) -> None:
        with self._lock:
            self._sessions += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots_published += 1

    def record_performance_report(self) -> None:
        with self._lock:
            self._performance_reports += 1

    def record_forecast_generated(self) -> None:
        with self._lock:
            self._forecasts += 1

    def record_request_completed(self, processing_ms: float) -> None:
        """Record a successfully completed request and update rolling latency."""
        with self._lock:
            if self._avg_response_ms == 0.0:
                self._avg_response_ms = processing_ms
            else:
                self._avg_response_ms = (
                    self._ema_alpha * processing_ms
                    + (1.0 - self._ema_alpha) * self._avg_response_ms
                )

    def record_request_failed(self) -> None:
        with self._lock:
            self._failed_requests += 1

    def record_request_rejected(self) -> None:
        with self._lock:
            self._rejected_requests += 1

    def record_availability_tick(self, *, is_up: bool) -> None:
        """
        Increment availability counters.

        Call once per health-check cycle.  ``is_up=True`` when the
        subsystem is operational.
        """
        with self._lock:
            self._total_ticks += 1
            if is_up:
                self._uptime_ticks += 1

    # ------------------------------------------------------------------
    # Accessors (properties)
    # ------------------------------------------------------------------
    @property
    def analytics_requests(self) -> int:
        with self._lock:
            return self._requests

    @property
    def analytics_sessions(self) -> int:
        with self._lock:
            return self._sessions

    @property
    def analytics_snapshots_published(self) -> int:
        with self._lock:
            return self._snapshots_published

    @property
    def performance_reports_generated(self) -> int:
        with self._lock:
            return self._performance_reports

    @property
    def forecasts_generated(self) -> int:
        with self._lock:
            return self._forecasts

    @property
    def failed_requests(self) -> int:
        with self._lock:
            return self._failed_requests

    @property
    def rejected_requests(self) -> int:
        with self._lock:
            return self._rejected_requests

    @property
    def subsystem_availability(self) -> float:
        """
        Rolling availability ratio in [0.0, 1.0].

        Returns 1.0 when no ticks have been recorded (subsystem not yet
        health-polled).
        """
        with self._lock:
            if self._total_ticks == 0:
                return 1.0
            return self._uptime_ticks / self._total_ticks

    @property
    def average_response_time_ms(self) -> float:
        """Exponential moving average of request processing latency (ms)."""
        with self._lock:
            return self._avg_response_ms

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """Return a plain-dict snapshot of all counters (no lock held)."""
        with self._lock:
            return {
                "analytics_requests":           self._requests,
                "analytics_sessions":           self._sessions,
                "analytics_snapshots_published": self._snapshots_published,
                "performance_reports_generated": self._performance_reports,
                "forecasts_generated":           self._forecasts,
                "failed_requests":               self._failed_requests,
                "rejected_requests":             self._rejected_requests,
                "subsystem_availability":        (
                    self._uptime_ticks / self._total_ticks
                    if self._total_ticks else 1.0
                ),
                "average_response_time_ms":      self._avg_response_ms,
            }

    def reset(self) -> None:
        """Reset all counters to zero (used on subsystem restart)."""
        with self._lock:
            self._requests            = 0
            self._sessions            = 0
            self._snapshots_published = 0
            self._performance_reports = 0
            self._forecasts           = 0
            self._failed_requests     = 0
            self._rejected_requests   = 0
            self._avg_response_ms     = 0.0
            self._uptime_ticks        = 0
            self._total_ticks         = 0
            self._created_at          = time.time()

    def __repr__(self) -> str:
        s = self.snapshot()
        return (
            f"AnalyticsIntegrationStatistics("
            f"requests={s['analytics_requests']}, "
            f"sessions={s['analytics_sessions']}, "
            f"snapshots={s['analytics_snapshots_published']}, "
            f"availability={s['subsystem_availability']:.2f}, "
            f"avg_ms={s['average_response_time_ms']:.1f})"
        )
