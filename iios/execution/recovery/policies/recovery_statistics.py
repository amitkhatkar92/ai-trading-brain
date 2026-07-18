"""
iios/execution/recovery/policies/recovery_statistics.py
=======================================================
RecoveryPolicyStatistics — thread-safe mutable accumulator for policy metrics.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict


class RecoveryPolicyStatistics:
    """
    Thread-safe accumulator for policy engine metrics.

    All write methods acquire the RLock.  Derived read-only properties
    (rates) also acquire it to ensure a consistent snapshot.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

        self._total_evaluations:       int   = 0
        self._total_decisions:         int   = 0
        self._approved_decisions:      int   = 0
        self._rejected_decisions:      int   = 0

        self._retry_recommendations:   int   = 0
        self._resume_recommendations:  int   = 0
        self._rollback_recommendations: int  = 0
        self._restart_recommendations: int   = 0
        self._failover_recommendations: int  = 0
        self._manual_interventions:    int   = 0
        self._emergency_shutdowns:     int   = 0
        self._fallback_used:           int   = 0

        self._total_evaluation_time_ms: float = 0.0
        self._evaluation_count_for_avg: int   = 0

    # ── Write methods ──────────────────────────────────────────────────────────

    def record_evaluation(self) -> None:
        with self._lock:
            self._total_evaluations += 1

    def record_decision(self, *, approved: bool) -> None:
        with self._lock:
            self._total_decisions += 1
            if approved:
                self._approved_decisions += 1
            else:
                self._rejected_decisions += 1

    def record_retry_recommendation(self) -> None:
        with self._lock:
            self._retry_recommendations += 1

    def record_resume_recommendation(self) -> None:
        with self._lock:
            self._resume_recommendations += 1

    def record_rollback_recommendation(self) -> None:
        with self._lock:
            self._rollback_recommendations += 1

    def record_restart_recommendation(self) -> None:
        with self._lock:
            self._restart_recommendations += 1

    def record_failover_recommendation(self) -> None:
        with self._lock:
            self._failover_recommendations += 1

    def record_manual_intervention(self) -> None:
        with self._lock:
            self._manual_interventions += 1

    def record_emergency_shutdown(self) -> None:
        with self._lock:
            self._emergency_shutdowns += 1

    def record_fallback_used(self) -> None:
        with self._lock:
            self._fallback_used += 1

    def record_evaluation_time(self, ms: float) -> None:
        with self._lock:
            self._total_evaluation_time_ms  += ms
            self._evaluation_count_for_avg  += 1

    # ── Read properties ───────────────────────────────────────────────────────

    @property
    def total_evaluations(self) -> int:
        with self._lock:
            return self._total_evaluations

    @property
    def total_decisions(self) -> int:
        with self._lock:
            return self._total_decisions

    @property
    def approved_decisions(self) -> int:
        with self._lock:
            return self._approved_decisions

    @property
    def rejected_decisions(self) -> int:
        with self._lock:
            return self._rejected_decisions

    @property
    def average_evaluation_time_ms(self) -> float:
        with self._lock:
            if self._evaluation_count_for_avg == 0:
                return 0.0
            return self._total_evaluation_time_ms / self._evaluation_count_for_avg

    def _rate(self, count: int, base: int) -> float:
        return count / base if base > 0 else 0.0

    @property
    def retry_rate(self) -> float:
        with self._lock:
            return self._rate(self._retry_recommendations, self._total_decisions)

    @property
    def rollback_rate(self) -> float:
        with self._lock:
            return self._rate(self._rollback_recommendations, self._total_decisions)

    @property
    def restart_rate(self) -> float:
        with self._lock:
            return self._rate(self._restart_recommendations, self._total_decisions)

    @property
    def failover_rate(self) -> float:
        with self._lock:
            return self._rate(self._failover_recommendations, self._total_decisions)

    @property
    def emergency_rate(self) -> float:
        with self._lock:
            return self._rate(self._emergency_shutdowns, self._total_decisions)

    # ── Utility ───────────────────────────────────────────────────────────────

    def copy(self) -> "RecoveryPolicyStatistics":
        """Return a deep copy (no lock held by caller needed)."""
        snap = RecoveryPolicyStatistics()
        with self._lock:
            snap._total_evaluations          = self._total_evaluations
            snap._total_decisions            = self._total_decisions
            snap._approved_decisions         = self._approved_decisions
            snap._rejected_decisions         = self._rejected_decisions
            snap._retry_recommendations      = self._retry_recommendations
            snap._resume_recommendations     = self._resume_recommendations
            snap._rollback_recommendations   = self._rollback_recommendations
            snap._restart_recommendations    = self._restart_recommendations
            snap._failover_recommendations   = self._failover_recommendations
            snap._manual_interventions       = self._manual_interventions
            snap._emergency_shutdowns        = self._emergency_shutdowns
            snap._fallback_used              = self._fallback_used
            snap._total_evaluation_time_ms   = self._total_evaluation_time_ms
            snap._evaluation_count_for_avg   = self._evaluation_count_for_avg
        return snap

    def reset(self) -> None:
        with self._lock:
            self.__init__()  # type: ignore[misc]

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_evaluations":        self._total_evaluations,
                "total_decisions":          self._total_decisions,
                "approved_decisions":       self._approved_decisions,
                "rejected_decisions":       self._rejected_decisions,
                "retry_recommendations":    self._retry_recommendations,
                "resume_recommendations":   self._resume_recommendations,
                "rollback_recommendations": self._rollback_recommendations,
                "restart_recommendations":  self._restart_recommendations,
                "failover_recommendations": self._failover_recommendations,
                "manual_interventions":     self._manual_interventions,
                "emergency_shutdowns":      self._emergency_shutdowns,
                "fallback_used":            self._fallback_used,
                "average_evaluation_time_ms": (
                    self._total_evaluation_time_ms / self._evaluation_count_for_avg
                    if self._evaluation_count_for_avg > 0 else 0.0
                ),
            }
