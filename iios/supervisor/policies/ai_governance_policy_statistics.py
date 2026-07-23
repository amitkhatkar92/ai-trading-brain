"""
ai_governance_policy_statistics.py — iios.supervisor.policies
--------------------------------------------------------------
Thread-safe statistics accumulator for the AI Governance Policy Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

_EMA_ALPHA = 0.1   # Exponential moving average smoothing factor


class AIGovernancePolicyStatistics:
    """
    Thread-safe accumulator for governance policy evaluation statistics.

    Tracks:
    - Evaluation counts (total, success, failure)
    - Action outcome counts (approved, rejected, blocked, escalated, …)
    - Emergency stop and human review counts
    - Policy evaluation throughput
    - Average / EMA evaluation latency
    - Governance coverage (evaluations with at least one non-default outcome)
    """

    def __init__(self) -> None:
        self._lock                    = threading.Lock()
        self._evaluations:      int   = 0
        self._successes:        int   = 0
        self._failures:         int   = 0
        self._approved:         int   = 0
        self._conditionally_approved: int = 0
        self._rejected:         int   = 0
        self._blocked:          int   = 0
        self._escalated:        int   = 0
        self._human_reviews:    int   = 0
        self._manual_reviews:   int   = 0
        self._emergency_stops:  int   = 0
        self._policies_evaluated: int = 0
        self._non_default_outcomes: int = 0   # for governance coverage
        self._total_elapsed_s:  float = 0.0
        self._ema_elapsed_s:    float = 0.0
        self._started_at:       float = time.time()

    # ------------------------------------------------------------------
    # Recorders
    # ------------------------------------------------------------------

    def record_evaluation(self) -> None:
        with self._lock:
            self._evaluations += 1

    def record_success(self, elapsed_s: float = 0.0) -> None:
        with self._lock:
            self._successes += 1
            self._total_elapsed_s += elapsed_s
            if elapsed_s > 0:
                self._ema_elapsed_s = (
                    _EMA_ALPHA * elapsed_s
                    + (1.0 - _EMA_ALPHA) * self._ema_elapsed_s
                ) if self._ema_elapsed_s > 0 else elapsed_s

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1

    def record_approved(self) -> None:
        with self._lock:
            self._approved += 1

    def record_conditionally_approved(self) -> None:
        with self._lock:
            self._conditionally_approved += 1

    def record_rejected(self) -> None:
        with self._lock:
            self._rejected += 1
            self._non_default_outcomes += 1

    def record_blocked(self) -> None:
        with self._lock:
            self._blocked += 1
            self._non_default_outcomes += 1

    def record_escalated(self) -> None:
        with self._lock:
            self._escalated += 1
            self._non_default_outcomes += 1

    def record_human_review(self) -> None:
        with self._lock:
            self._human_reviews += 1
            self._non_default_outcomes += 1

    def record_manual_review(self) -> None:
        with self._lock:
            self._manual_reviews += 1

    def record_emergency_stop(self) -> None:
        with self._lock:
            self._emergency_stops += 1
            self._non_default_outcomes += 1

    def record_policies_evaluated(self, count: int) -> None:
        with self._lock:
            self._policies_evaluated += count

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = (
                self._total_elapsed_s / self._successes
                if self._successes > 0 else 0.0
            )
            coverage = (
                self._non_default_outcomes / self._evaluations
                if self._evaluations > 0 else 0.0
            )
            return {
                "evaluations":              self._evaluations,
                "successes":                self._successes,
                "failures":                 self._failures,
                "approved":                 self._approved,
                "conditionally_approved":   self._conditionally_approved,
                "rejected":                 self._rejected,
                "blocked":                  self._blocked,
                "escalated":                self._escalated,
                "human_reviews":            self._human_reviews,
                "manual_reviews":           self._manual_reviews,
                "emergency_stops":          self._emergency_stops,
                "policies_evaluated":       self._policies_evaluated,
                "average_evaluation_s":     avg,
                "ema_evaluation_s":         self._ema_elapsed_s,
                "governance_coverage":      coverage,
                "uptime_s":                 time.time() - self._started_at,
            }

    def reset(self) -> None:
        with self._lock:
            self._evaluations             = 0
            self._successes               = 0
            self._failures                = 0
            self._approved                = 0
            self._conditionally_approved  = 0
            self._rejected                = 0
            self._blocked                 = 0
            self._escalated               = 0
            self._human_reviews           = 0
            self._manual_reviews          = 0
            self._emergency_stops         = 0
            self._policies_evaluated      = 0
            self._non_default_outcomes    = 0
            self._total_elapsed_s         = 0.0
            self._ema_elapsed_s           = 0.0
            self._started_at              = time.time()
