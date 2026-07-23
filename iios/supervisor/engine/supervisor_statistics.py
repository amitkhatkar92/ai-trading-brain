"""
supervisor_statistics.py — iios.supervisor.engine
--------------------------------------------------
Thread-safe running statistics for the Supervisor Engine.

Uses Welford's online algorithm for numerically stable mean and variance
of workflow elapsed times.  Also maintains a rolling throughput window.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import collections
import math
import threading
import time


class SupervisorEngineStatistics:
    """
    Thread-safe statistics accumulator for the Supervisor Engine.

    Tracks:
    - Counters: sessions, requests, responses, pipelines, health checks,
      subsystems supervised
    - Success / failure counts
    - Welford online mean / variance of workflow elapsed seconds
    - Rolling throughput over a configurable window
    """

    def __init__(self, throughput_window_s: float = 60.0) -> None:
        self._lock            = threading.Lock()
        self._window          = throughput_window_s
        self._ts_deque: collections.deque = collections.deque()

        self._total_sessions:         int   = 0
        self._total_requests:         int   = 0
        self._total_responses:        int   = 0
        self._total_pipelines:        int   = 0
        self._total_snapshots:        int   = 0
        self._total_health_checks:    int   = 0
        self._total_subsystems:       int   = 0
        self._total_success:          int   = 0
        self._total_failure:          int   = 0

        # Welford: n, mean, M2
        self._n:     int   = 0
        self._mean:  float = 0.0
        self._m2:    float = 0.0

    # ------------------------------------------------------------------
    # Increment helpers
    # ------------------------------------------------------------------

    def record_session(self) -> None:
        with self._lock:
            self._total_sessions += 1

    def record_request(self) -> None:
        with self._lock:
            self._total_requests += 1

    def record_response(self, *, success: bool) -> None:
        with self._lock:
            self._total_responses += 1
            if success:
                self._total_success += 1
            else:
                self._total_failure += 1

    def record_pipeline(self) -> None:
        with self._lock:
            self._total_pipelines += 1

    def record_snapshot(self) -> None:
        with self._lock:
            self._total_snapshots += 1

    def record_health_check(self) -> None:
        with self._lock:
            self._total_health_checks += 1

    def record_subsystem(self) -> None:
        with self._lock:
            self._total_subsystems += 1

    # ------------------------------------------------------------------
    # Workflow timing
    # ------------------------------------------------------------------

    def record_elapsed(self, elapsed_s: float) -> None:
        """Update Welford mean / variance and throughput window."""
        now = time.time()
        with self._lock:
            self._n += 1
            delta        = elapsed_s - self._mean
            self._mean  += delta / self._n
            delta2       = elapsed_s - self._mean
            self._m2    += delta * delta2
            self._ts_deque.append(now)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def mean_elapsed_s(self) -> float:
        with self._lock:
            return self._mean

    @property
    def stddev_elapsed_s(self) -> float:
        with self._lock:
            if self._n < 2:
                return 0.0
            return math.sqrt(self._m2 / (self._n - 1))

    def throughput_per_minute(self) -> float:
        """Requests completed in the last *throughput_window_s* seconds."""
        now    = time.time()
        cutoff = now - self._window
        with self._lock:
            while self._ts_deque and self._ts_deque[0] < cutoff:
                self._ts_deque.popleft()
            count = len(self._ts_deque)
        window_min = self._window / 60.0
        return count / window_min if window_min > 0 else 0.0

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        # Compute throughput OUTSIDE the lock to avoid re-entrant deadlock
        # (throughput_per_minute also acquires self._lock).
        throughput = self.throughput_per_minute()
        with self._lock:
            return {
                "total_sessions":         self._total_sessions,
                "total_requests":         self._total_requests,
                "total_responses":        self._total_responses,
                "total_pipelines":        self._total_pipelines,
                "total_snapshots":        self._total_snapshots,
                "total_health_checks":    self._total_health_checks,
                "total_subsystems":       self._total_subsystems,
                "total_success":          self._total_success,
                "total_failure":          self._total_failure,
                "mean_elapsed_s":         self._mean,
                "stddev_elapsed_s":       (
                    math.sqrt(self._m2 / (self._n - 1))
                    if self._n >= 2 else 0.0
                ),
                "completed_workflows":    self._n,
                "throughput_per_minute":  throughput,
            }

    def reset(self) -> None:
        with self._lock:
            self.__init__(self._window)   # type: ignore[misc]
