"""
decision_optimization_statistics.py — iios.decision.optimization
=================================================================
Thread-safe runtime statistics for the Decision Optimization Framework.

Eight counters (matching the spec)
-----------------------------------
1. optimization_requests       — total requests received
2. candidates_evaluated        — total candidates processed
3. solutions_generated         — total successful solutions
4. optimization_success_rate   — EMA of success fraction
5. average_optimization_time_s — EMA wall-clock time
6. average_candidate_count     — EMA candidates per request
7. constraint_violations       — total hard violations observed
8. optimization_throughput     — solutions in last 60 s

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque

from .constants import EMA_ALPHA, THROUGHPUT_WINDOW_S


class DecisionOptimizationStatistics:
    """Thread-safe runtime statistics for the optimization engine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

        self._requests          = 0
        self._candidates        = 0
        self._solutions         = 0
        self._violations        = 0

        self._success_rate      = 0.0
        self._avg_time          = 0.0
        self._avg_candidates    = 0.0

        self._window: Deque[float] = deque()

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def record_request_started(self, candidate_count: int) -> None:
        with self._lock:
            self._requests       += 1
            self._candidates     += candidate_count
            # EMA for average candidate count
            self._avg_candidates  = (
                EMA_ALPHA * candidate_count + (1.0 - EMA_ALPHA) * self._avg_candidates
            )

    def record_request_completed(
        self,
        *,
        success:           bool,
        evaluation_time_s: float,
        violations:        int = 0,
    ) -> None:
        with self._lock:
            if success:
                self._solutions += 1

            self._violations += violations

            # EMA updates
            success_val         = 1.0 if success else 0.0
            self._success_rate  = EMA_ALPHA * success_val + (1.0 - EMA_ALPHA) * self._success_rate
            self._avg_time      = EMA_ALPHA * evaluation_time_s + (1.0 - EMA_ALPHA) * self._avg_time

            # Throughput
            now = time.monotonic()
            self._window.append(now)
            cutoff = now - THROUGHPUT_WINDOW_S
            while self._window and self._window[0] < cutoff:
                self._window.popleft()

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "optimization_requests":       self._requests,
                "candidates_evaluated":        self._candidates,
                "solutions_generated":         self._solutions,
                "optimization_success_rate":   self._success_rate,
                "average_optimization_time_s": self._avg_time,
                "average_candidate_count":     self._avg_candidates,
                "constraint_violations":       self._violations,
                "optimization_throughput":     len(self._window),
            }

    def reset(self) -> None:
        with self._lock:
            self._requests       = 0
            self._candidates     = 0
            self._solutions      = 0
            self._violations     = 0
            self._success_rate   = 0.0
            self._avg_time       = 0.0
            self._avg_candidates = 0.0
            self._window.clear()
