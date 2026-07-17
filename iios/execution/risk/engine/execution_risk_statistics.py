"""iios/execution/risk/engine/execution_risk_statistics.py
==================================================
EngineRiskStatistics — aggregated operation counters, timing averages,
and rule execution metrics for the Execution Risk Engine.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class EngineRiskStatistics:
    """
    Mutable statistics accumulator for the RiskManager and RiskEngine.

    Counters are incremented by the manager as evaluations progress.
    Thread safety is the caller's responsibility.
    """

    # ── Evaluation lifecycle counters ─────────────────────────────────────────
    evaluations_started:   int = 0
    evaluations_completed: int = 0
    evaluations_failed:    int = 0
    evaluations_passed:    int = 0
    evaluations_warned:    int = 0
    evaluations_blocked:   int = 0
    evaluations_archived:  int = 0

    # ── Rule execution counters ───────────────────────────────────────────────
    rule_executions_total:   int = 0
    rule_executions_passed:  int = 0
    rule_executions_warned:  int = 0
    rule_executions_blocked: int = 0
    rule_executions_errored: int = 0
    rule_executions_skipped: int = 0

    # ── Timing accumulation ───────────────────────────────────────────────────
    total_evaluation_time_ms:  float = 0.0
    total_aggregation_time_ms: float = 0.0

    # ── Totals ────────────────────────────────────────────────────────────────
    total_operations:  int = 0
    failed_operations: int = 0

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def average_evaluation_time_ms(self) -> float:
        """Mean evaluation time in milliseconds for completed evaluations."""
        if self.evaluations_completed == 0:
            return 0.0
        return self.total_evaluation_time_ms / self.evaluations_completed

    @property
    def average_aggregation_time_ms(self) -> float:
        """Mean aggregation time in milliseconds."""
        if self.evaluations_completed == 0:
            return 0.0
        return self.total_aggregation_time_ms / self.evaluations_completed

    @property
    def pass_rate(self) -> float:
        """Fraction of completed evaluations that passed (PASSED + WARNING)."""
        completed = self.evaluations_completed
        if completed == 0:
            return 0.0
        return (self.evaluations_passed + self.evaluations_warned) / completed

    @property
    def block_rate(self) -> float:
        """Fraction of completed evaluations that were blocked."""
        if self.evaluations_completed == 0:
            return 0.0
        return self.evaluations_blocked / self.evaluations_completed

    @property
    def success_rate(self) -> float:
        """Fraction of all operations that succeeded (0–1)."""
        if self.total_operations == 0:
            return 1.0
        return (self.total_operations - self.failed_operations) / self.total_operations

    @property
    def failure_count(self) -> int:
        return self.failed_operations

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def touch(self) -> None:
        self.last_updated_at = time.time()

    def record_started(self, elapsed_ms: float = 0.0) -> None:
        self.evaluations_started += 1
        self.total_operations    += 1
        self.touch()

    def record_completed_passed(self, evaluation_ms: float = 0.0, aggregation_ms: float = 0.0) -> None:
        self.evaluations_completed       += 1
        self.evaluations_passed          += 1
        self.total_evaluation_time_ms    += evaluation_ms
        self.total_aggregation_time_ms   += aggregation_ms
        self.touch()

    def record_completed_warned(self, evaluation_ms: float = 0.0, aggregation_ms: float = 0.0) -> None:
        self.evaluations_completed       += 1
        self.evaluations_warned          += 1
        self.total_evaluation_time_ms    += evaluation_ms
        self.total_aggregation_time_ms   += aggregation_ms
        self.touch()

    def record_completed_blocked(self, evaluation_ms: float = 0.0, aggregation_ms: float = 0.0) -> None:
        self.evaluations_completed       += 1
        self.evaluations_blocked         += 1
        self.total_evaluation_time_ms    += evaluation_ms
        self.total_aggregation_time_ms   += aggregation_ms
        self.touch()

    def record_failed(self) -> None:
        self.evaluations_failed  += 1
        self.failed_operations   += 1
        self.total_operations    += 1
        self.touch()

    def record_archived(self) -> None:
        self.evaluations_archived += 1
        self.touch()

    def record_rule_execution(
        self,
        *,
        passed:  int = 0,
        warned:  int = 0,
        blocked: int = 0,
        errored: int = 0,
        skipped: int = 0,
    ) -> None:
        total = passed + warned + blocked + errored + skipped
        self.rule_executions_total   += total
        self.rule_executions_passed  += passed
        self.rule_executions_warned  += warned
        self.rule_executions_blocked += blocked
        self.rule_executions_errored += errored
        self.rule_executions_skipped += skipped
        self.touch()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluations_started":       self.evaluations_started,
            "evaluations_completed":     self.evaluations_completed,
            "evaluations_failed":        self.evaluations_failed,
            "evaluations_passed":        self.evaluations_passed,
            "evaluations_warned":        self.evaluations_warned,
            "evaluations_blocked":       self.evaluations_blocked,
            "evaluations_archived":      self.evaluations_archived,
            "rule_executions_total":     self.rule_executions_total,
            "rule_executions_passed":    self.rule_executions_passed,
            "rule_executions_warned":    self.rule_executions_warned,
            "rule_executions_blocked":   self.rule_executions_blocked,
            "rule_executions_errored":   self.rule_executions_errored,
            "rule_executions_skipped":   self.rule_executions_skipped,
            "total_evaluation_time_ms":  self.total_evaluation_time_ms,
            "total_aggregation_time_ms": self.total_aggregation_time_ms,
            "average_evaluation_time_ms":  self.average_evaluation_time_ms,
            "average_aggregation_time_ms": self.average_aggregation_time_ms,
            "total_operations":          self.total_operations,
            "failed_operations":         self.failed_operations,
            "pass_rate":                 self.pass_rate,
            "block_rate":                self.block_rate,
            "success_rate":              self.success_rate,
            "last_updated_at":           self.last_updated_at,
        }
