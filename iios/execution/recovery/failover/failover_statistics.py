"""
iios/execution/recovery/failover/failover_statistics.py
=======================================================
FailoverStatistics — thread-safe accumulator for failover metrics.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict


class FailoverStatistics:
    """Thread-safe statistics accumulator for the Failover Engine."""

    def __init__(self) -> None:
        self._lock = threading.RLock()

        self._failovers_executed:        int   = 0
        self._successful_failovers:      int   = 0
        self._failed_failovers:          int   = 0
        self._fallback_executions:       int   = 0
        self._manual_escalations:        int   = 0
        self._verification_runs:         int   = 0
        self._verification_passed:       int   = 0
        self._verification_failed:       int   = 0

        # Per-action counters
        self._action_counts: Dict[str, int] = {}
        # Per-type counters
        self._type_counts: Dict[str, int] = {}

        self._total_recovery_time_ms:    float = 0.0
        self._recovery_count_for_avg:    int   = 0

    # ── Writes ────────────────────────────────────────────────────────────────

    def record_execution(self, *, action: str = "", failover_type: str = "") -> None:
        with self._lock:
            self._failovers_executed += 1
            if action:
                self._action_counts[action] = self._action_counts.get(action, 0) + 1
            if failover_type:
                self._type_counts[failover_type] = self._type_counts.get(failover_type, 0) + 1

    def record_success(self) -> None:
        with self._lock:
            self._successful_failovers += 1

    def record_failure(self) -> None:
        with self._lock:
            self._failed_failovers += 1

    def record_fallback(self) -> None:
        with self._lock:
            self._fallback_executions += 1

    def record_manual_escalation(self) -> None:
        with self._lock:
            self._manual_escalations += 1

    def record_verification_run(self, *, passed: bool) -> None:
        with self._lock:
            self._verification_runs += 1
            if passed:
                self._verification_passed += 1
            else:
                self._verification_failed += 1

    def record_recovery_time(self, ms: float) -> None:
        with self._lock:
            self._total_recovery_time_ms  += ms
            self._recovery_count_for_avg  += 1

    # ── Reads ─────────────────────────────────────────────────────────────────

    @property
    def failovers_executed(self) -> int:
        with self._lock:
            return self._failovers_executed

    @property
    def successful_failovers(self) -> int:
        with self._lock:
            return self._successful_failovers

    @property
    def failed_failovers(self) -> int:
        with self._lock:
            return self._failed_failovers

    @property
    def fallback_executions(self) -> int:
        with self._lock:
            return self._fallback_executions

    @property
    def average_recovery_time_ms(self) -> float:
        with self._lock:
            if self._recovery_count_for_avg == 0:
                return 0.0
            return self._total_recovery_time_ms / self._recovery_count_for_avg

    @property
    def verification_success_rate(self) -> float:
        with self._lock:
            if self._verification_runs == 0:
                return 0.0
            return self._verification_passed / self._verification_runs

    @property
    def success_rate(self) -> float:
        with self._lock:
            if self._failovers_executed == 0:
                return 0.0
            return self._successful_failovers / self._failovers_executed

    def action_count(self, action: str) -> int:
        with self._lock:
            return self._action_counts.get(action, 0)

    def type_count(self, failover_type: str) -> int:
        with self._lock:
            return self._type_counts.get(failover_type, 0)

    # ── Utility ───────────────────────────────────────────────────────────────

    def copy(self) -> "FailoverStatistics":
        snap = FailoverStatistics()
        with self._lock:
            snap._failovers_executed      = self._failovers_executed
            snap._successful_failovers    = self._successful_failovers
            snap._failed_failovers        = self._failed_failovers
            snap._fallback_executions     = self._fallback_executions
            snap._manual_escalations      = self._manual_escalations
            snap._verification_runs       = self._verification_runs
            snap._verification_passed     = self._verification_passed
            snap._verification_failed     = self._verification_failed
            snap._action_counts           = dict(self._action_counts)
            snap._type_counts             = dict(self._type_counts)
            snap._total_recovery_time_ms  = self._total_recovery_time_ms
            snap._recovery_count_for_avg  = self._recovery_count_for_avg
        return snap

    def reset(self) -> None:
        with self._lock:
            self.__init__()  # type: ignore[misc]

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "failovers_executed":        self._failovers_executed,
                "successful_failovers":      self._successful_failovers,
                "failed_failovers":          self._failed_failovers,
                "fallback_executions":       self._fallback_executions,
                "manual_escalations":        self._manual_escalations,
                "verification_runs":         self._verification_runs,
                "verification_passed":       self._verification_passed,
                "verification_failed":       self._verification_failed,
                "average_recovery_time_ms":  (
                    self._total_recovery_time_ms / self._recovery_count_for_avg
                    if self._recovery_count_for_avg > 0 else 0.0
                ),
                "success_rate":              (
                    self._successful_failovers / self._failovers_executed
                    if self._failovers_executed > 0 else 0.0
                ),
                "action_counts":             dict(self._action_counts),
                "type_counts":               dict(self._type_counts),
            }
