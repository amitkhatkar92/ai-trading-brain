"""
decision_integration_statistics.py — iios.decision.integration
===============================================================
Thread-safe statistics tracker for the Decision Integration subsystem.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict

from .constants import EMA_ALPHA, THROUGHPUT_WINDOW_S


class DecisionIntegrationStatistics:
    """
    Thread-safe statistics tracker.

    Tracks
    ------
    - Total requests submitted, completed, failed
    - In-flight request count
    - Snapshot publications
    - Policy evaluations
    - Optimized decisions
    - Session creations
    - EMA of response time
    - Average response time
    - Throughput (requests/minute in sliding window)
    """

    def __init__(self) -> None:
        self._lock:                  threading.Lock = threading.Lock()
        self._requests_submitted:    int            = 0
        self._requests_completed:    int            = 0
        self._requests_failed:       int            = 0
        self._requests_in_flight:    int            = 0
        self._sessions_created:      int            = 0
        self._snapshots_published:   int            = 0
        self._policy_evaluations:    int            = 0
        self._optimized_decisions:   int            = 0
        self._total_response_time_s: float          = 0.0
        self._ema_response_time_s:   float          = 0.0
        self._timestamps:            Deque[float]   = deque()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_request_submitted(self) -> None:
        with self._lock:
            self._requests_submitted += 1
            self._requests_in_flight += 1

    def record_request_completed(self, response_time_s: float = 0.0) -> None:
        with self._lock:
            self._requests_completed += 1
            self._requests_in_flight = max(0, self._requests_in_flight - 1)
            self._total_response_time_s += response_time_s
            if self._requests_completed == 1:
                self._ema_response_time_s = response_time_s
            else:
                self._ema_response_time_s = (
                    EMA_ALPHA * response_time_s
                    + (1.0 - EMA_ALPHA) * self._ema_response_time_s
                )
            self._timestamps.append(time.monotonic())

    def record_request_failed(self, response_time_s: float = 0.0) -> None:
        with self._lock:
            self._requests_failed += 1
            self._requests_in_flight = max(0, self._requests_in_flight - 1)
            self._total_response_time_s += response_time_s
            self._timestamps.append(time.monotonic())

    def record_session_created(self) -> None:
        with self._lock:
            self._sessions_created += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots_published += 1

    def record_policy_evaluation(self) -> None:
        with self._lock:
            self._policy_evaluations += 1

    def record_optimized_decision(self) -> None:
        with self._lock:
            self._optimized_decisions += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a dict of current statistics."""
        with self._lock:
            completed = self._requests_completed
            total_s   = self._total_response_time_s

            # Evict old timestamps
            cutoff = time.monotonic() - THROUGHPUT_WINDOW_S
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()
            window_count = len(self._timestamps)

            avg_s   = (total_s / completed) if completed > 0 else 0.0
            throughput = (window_count / THROUGHPUT_WINDOW_S) * 60.0  # per minute

            total = self._requests_submitted
            failed = self._requests_failed
            subsystem_availability = (
                round((completed / total) * 100.0, 2) if total > 0 else 100.0
            )

            return {
                "requests_submitted":      self._requests_submitted,
                "requests_completed":      completed,
                "requests_failed":         failed,
                "requests_in_flight":      self._requests_in_flight,
                "sessions_created":        self._sessions_created,
                "snapshots_published":     self._snapshots_published,
                "policy_evaluations":      self._policy_evaluations,
                "optimized_decisions":     self._optimized_decisions,
                "average_response_time_s": avg_s,
                "ema_response_time_s":     self._ema_response_time_s,
                "throughput_per_minute":   throughput,
                "subsystem_availability":  subsystem_availability,
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._requests_submitted    = 0
            self._requests_completed    = 0
            self._requests_failed       = 0
            self._requests_in_flight    = 0
            self._sessions_created      = 0
            self._snapshots_published   = 0
            self._policy_evaluations    = 0
            self._optimized_decisions   = 0
            self._total_response_time_s = 0.0
            self._ema_response_time_s   = 0.0
            self._timestamps.clear()
