"""
risk_policy_statistics.py — iios.risk.policies
================================================
Thread-safe evaluation statistics for the Risk Policy Framework.

Tracks the 9 core statistics required by the specification:
  Policies Evaluated, Approved, Rejected, Blocked, Escalated,
  Immediate Actions Triggered, Average Evaluation Time,
  Policy Coverage, Evaluation Throughput.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class RiskPolicyStatistics:
    """
    Thread-safe running statistics for the Risk Policy Framework.

    All counter increments acquire an internal reentrant lock, making this
    safe for concurrent use from multiple evaluator threads.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reset()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_evaluation(self) -> None:
        with self._lock:
            self._evaluations_total += 1

    def record_approved(self) -> None:
        with self._lock:
            self._approved += 1

    def record_conditionally_approved(self) -> None:
        with self._lock:
            self._conditionally_approved += 1

    def record_rejected(self) -> None:
        with self._lock:
            self._rejected += 1

    def record_blocked(self) -> None:
        with self._lock:
            self._blocked += 1

    def record_escalated(self) -> None:
        with self._lock:
            self._escalated += 1

    def record_deferred(self) -> None:
        with self._lock:
            self._deferred += 1

    def record_manual_review(self) -> None:
        with self._lock:
            self._manual_review += 1

    def record_immediate_action(self) -> None:
        with self._lock:
            self._immediate_actions += 1

    def record_evaluation_time(self, elapsed_s: float) -> None:
        """Record the elapsed time (seconds) for one complete evaluation run."""
        with self._lock:
            self._total_elapsed_s += elapsed_s
            self._timed_evaluations += 1

    def record_policies_evaluated(self, count: int) -> None:
        """Record number of policies evaluated in a single run."""
        with self._lock:
            self._policies_evaluated_total += count

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return an atomic snapshot of all statistics."""
        with self._lock:
            avg_time = (
                self._total_elapsed_s / self._timed_evaluations
                if self._timed_evaluations > 0
                else 0.0
            )
            # Policy coverage: ratio of evaluations that produced at least
            # one policy result vs total evaluations
            policy_coverage = (
                self._policies_evaluated_total / max(self._evaluations_total, 1)
            )
            # Throughput: evaluations per second since statistics were reset
            elapsed_since_reset = time.time() - self._reset_time
            throughput = (
                self._evaluations_total / elapsed_since_reset
                if elapsed_since_reset > 0
                else 0.0
            )
            return {
                "evaluations_total":         self._evaluations_total,
                "approved":                  self._approved,
                "conditionally_approved":    self._conditionally_approved,
                "rejected":                  self._rejected,
                "blocked":                   self._blocked,
                "escalated":                 self._escalated,
                "deferred":                  self._deferred,
                "manual_review_required":    self._manual_review,
                "immediate_actions_triggered": self._immediate_actions,
                "average_evaluation_time_s": avg_time,
                "policy_coverage":           policy_coverage,
                "evaluation_throughput_per_s": throughput,
                "policies_evaluated_total":  self._policies_evaluated_total,
            }

    def reset(self) -> None:
        with self._lock:
            self._reset()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._evaluations_total:      int   = 0
        self._approved:               int   = 0
        self._conditionally_approved: int   = 0
        self._rejected:               int   = 0
        self._blocked:                int   = 0
        self._escalated:              int   = 0
        self._deferred:               int   = 0
        self._manual_review:          int   = 0
        self._immediate_actions:      int   = 0
        self._total_elapsed_s:        float = 0.0
        self._timed_evaluations:      int   = 0
        self._policies_evaluated_total: int = 0
        self._reset_time:             float = time.time()
