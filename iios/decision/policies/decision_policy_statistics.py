"""
decision_policy_statistics.py — iios.decision.policies
========================================================
Thread-safe runtime statistics for the Decision Policy Framework.

Eight counters (matching the spec)
-----------------------------------
1. policies_evaluated       — total evaluations started
2. policies_approved        — APPROVE or APPROVE_WITH_CONDITIONS outcomes
3. policies_rejected        — REJECT outcomes
4. policies_blocked         — BLOCK outcomes
5. policies_escalated       — ESCALATE or REQUIRE_MANUAL_REVIEW outcomes
6. average_evaluation_time_s — EMA (α = EMA_ALPHA) of wall-clock eval time
7. policy_coverage           — latest coverage fraction (0.0 – 1.0)
8. evaluation_throughput     — evaluations completed in the last 60 s

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque

from .constants import (
    APPROVAL_ACTIONS,
    EMA_ALPHA,
    THROUGHPUT_WINDOW_S,
    PolicyAction,
)


class DecisionPolicyStatistics:
    """
    Thread-safe runtime statistics for the Decision Policy Framework.

    Usage
    -----
    stats.record_evaluation_started()           # before evaluation
    stats.record_evaluation_completed(action, t) # after evaluation
    stats.record_coverage(fraction)              # after registry query
    snap = stats.snapshot()                      # read all 8 counters
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # Raw counters
        self._evaluated  = 0
        self._approved   = 0
        self._rejected   = 0
        self._blocked    = 0
        self._escalated  = 0

        # EMA
        self._avg_time   = 0.0

        # Coverage (latest fraction observed)
        self._coverage   = 0.0

        # Sliding-window throughput: timestamps of recent completions
        self._window: Deque[float] = deque()

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def record_evaluation_started(self) -> None:
        with self._lock:
            self._evaluated += 1

    def record_evaluation_completed(
        self,
        action: PolicyAction,
        evaluation_time_s: float,
    ) -> None:
        """
        Update counters after one full evaluation completes.

        Parameters
        ----------
        action :             The final resolved action.
        evaluation_time_s :  Wall-clock time taken for the evaluation.
        """
        with self._lock:
            if action in APPROVAL_ACTIONS:
                self._approved += 1
            elif action == PolicyAction.REJECT:
                self._rejected += 1
            elif action == PolicyAction.BLOCK:
                self._blocked += 1
            else:
                # ESCALATE, REQUIRE_MANUAL_REVIEW, DEFER all go to escalated
                self._escalated += 1

            # EMA update
            self._avg_time = (
                EMA_ALPHA * evaluation_time_s + (1.0 - EMA_ALPHA) * self._avg_time
            )

            # Sliding-window throughput
            now = time.monotonic()
            self._window.append(now)
            cutoff = now - THROUGHPUT_WINDOW_S
            while self._window and self._window[0] < cutoff:
                self._window.popleft()

    def record_coverage(self, fraction: float) -> None:
        with self._lock:
            self._coverage = max(0.0, min(1.0, fraction))

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Return all 8 counters as a plain dict."""
        with self._lock:
            return {
                "policies_evaluated":        self._evaluated,
                "policies_approved":         self._approved,
                "policies_rejected":         self._rejected,
                "policies_blocked":          self._blocked,
                "policies_escalated":        self._escalated,
                "average_evaluation_time_s": self._avg_time,
                "policy_coverage":           self._coverage,
                "evaluation_throughput":     len(self._window),
            }

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._evaluated = 0
            self._approved  = 0
            self._rejected  = 0
            self._blocked   = 0
            self._escalated = 0
            self._avg_time  = 0.0
            self._coverage  = 0.0
            self._window.clear()
