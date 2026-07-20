"""
decision_statistics.py — iios.decision.engine
===============================================
Thread-safe statistics container for the Decision Engine subsystem.

Tracks the eight counters mandated by the specification.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

from .constants import EMA_ALPHA


class DecisionEngineStatistics:
    """
    Thread-safe statistics for the institutional decision engine.

    Eight tracked metrics
    ---------------------
    1.  **Decision Sessions**       — total sessions created.
    2.  **Decision Requests**       — total requests submitted.
    3.  **Decision Pipelines**      — total pipelines executed.
    4.  **Average Decision Time**   — EMA of end-to-end decision seconds.
    5.  **Average Collection Time** — EMA of collection phase seconds.
    6.  **Average Dispatch Time**   — EMA of dispatch/evaluation seconds.
    7.  **Subsystem Availability**  — rolling fraction of healthy checks (0–1).
    8.  **Decision Throughput**     — requests per minute (sliding window).
    """

    _THROUGHPUT_WINDOW_S: float = 60.0   # one-minute sliding window

    def __init__(self) -> None:
        self._lock = threading.Lock()

        self._sessions_created:   int   = 0
        self._requests_submitted: int   = 0
        self._pipelines_executed: int   = 0

        # EMA counters
        self._avg_decision_time_s:   float = 0.0
        self._avg_collection_time_s: float = 0.0
        self._avg_dispatch_time_s:   float = 0.0
        self._ema_alpha:             float = EMA_ALPHA

        # Subsystem availability: count of health checks
        self._health_total:   int = 0
        self._health_healthy: int = 0

        # Throughput: timestamps of recent completions
        self._completion_timestamps: list[float] = []

        self._created_at = time.time()

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------
    def record_session_created(self) -> None:
        with self._lock:
            self._sessions_created += 1

    def record_request_submitted(self) -> None:
        with self._lock:
            self._requests_submitted += 1

    def record_pipeline_executed(
        self,
        *,
        total_time_s:      float = 0.0,
        collection_time_s: float = 0.0,
        dispatch_time_s:   float = 0.0,
    ) -> None:
        """Record a completed pipeline and update all time averages."""
        with self._lock:
            self._pipelines_executed += 1
            self._avg_decision_time_s   = self._ema(self._avg_decision_time_s,   total_time_s)
            self._avg_collection_time_s = self._ema(self._avg_collection_time_s, collection_time_s)
            self._avg_dispatch_time_s   = self._ema(self._avg_dispatch_time_s,   dispatch_time_s)
            now = time.time()
            self._completion_timestamps.append(now)

    def record_health_check(self, healthy: bool) -> None:
        """Update the subsystem availability counter."""
        with self._lock:
            self._health_total   += 1
            if healthy:
                self._health_healthy += 1

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def decision_sessions(self) -> int:
        with self._lock:
            return self._sessions_created

    @property
    def decision_requests(self) -> int:
        with self._lock:
            return self._requests_submitted

    @property
    def decision_pipelines(self) -> int:
        with self._lock:
            return self._pipelines_executed

    @property
    def average_decision_time_s(self) -> float:
        with self._lock:
            return self._avg_decision_time_s

    @property
    def average_collection_time_s(self) -> float:
        with self._lock:
            return self._avg_collection_time_s

    @property
    def average_dispatch_time_s(self) -> float:
        with self._lock:
            return self._avg_dispatch_time_s

    @property
    def subsystem_availability(self) -> float:
        """Fraction of subsystem health checks that returned healthy (0–1)."""
        with self._lock:
            if self._health_total == 0:
                return 1.0
            return self._health_healthy / self._health_total

    @property
    def decision_throughput(self) -> float:
        """Completed decisions per minute over the last 60-second window."""
        with self._lock:
            now     = time.time()
            cutoff  = now - self._THROUGHPUT_WINDOW_S
            # Evict old timestamps
            self._completion_timestamps = [
                t for t in self._completion_timestamps if t >= cutoff
            ]
            return len(self._completion_timestamps)  # count per minute

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """Return a plain-dict snapshot of all eight counters."""
        with self._lock:
            now    = time.time()
            cutoff = now - self._THROUGHPUT_WINDOW_S
            recent = [t for t in self._completion_timestamps if t >= cutoff]
            return {
                "decision_sessions":          self._sessions_created,
                "decision_requests":          self._requests_submitted,
                "decision_pipelines":         self._pipelines_executed,
                "average_decision_time_s":    self._avg_decision_time_s,
                "average_collection_time_s":  self._avg_collection_time_s,
                "average_dispatch_time_s":    self._avg_dispatch_time_s,
                "subsystem_availability":     (
                    self._health_healthy / self._health_total
                    if self._health_total else 1.0
                ),
                "decision_throughput":        float(len(recent)),
            }

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._sessions_created        = 0
            self._requests_submitted      = 0
            self._pipelines_executed      = 0
            self._avg_decision_time_s     = 0.0
            self._avg_collection_time_s   = 0.0
            self._avg_dispatch_time_s     = 0.0
            self._health_total            = 0
            self._health_healthy          = 0
            self._completion_timestamps   = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ema(self, current: float, new_value: float) -> float:
        if current == 0.0:
            return new_value
        return self._ema_alpha * new_value + (1.0 - self._ema_alpha) * current
