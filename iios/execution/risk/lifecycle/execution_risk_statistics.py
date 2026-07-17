"""iios/execution/risk/lifecycle/execution_risk_statistics.py
==================================================
RiskStatistics — aggregated counters and averages for the
Execution Risk Lifecycle registry.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RiskStatistics:
    """
    Mutable statistics accumulator for a RiskRegistry.

    All numeric fields start at zero and are incremented by the registry
    as evaluations change state.  Thread safety is the registry's responsibility.
    """

    # ── Evaluation counts ─────────────────────────────────────────────────────
    evaluations_created:    int = 0
    evaluations_passed:     int = 0
    evaluations_warned:     int = 0
    evaluations_blocked:    int = 0
    evaluations_overridden: int = 0
    evaluations_expired:    int = 0
    evaluations_failed:     int = 0
    evaluations_archived:   int = 0

    # ── Transition counters ───────────────────────────────────────────────────
    total_transitions: int = 0
    override_count:    int = 0

    # ── Lifecycle time accumulation ───────────────────────────────────────────
    total_evaluation_time_ms: float = 0.0

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def average_evaluation_time_ms(self) -> float:
        """Mean evaluation time in ms for completed (PASSED/WARNING/BLOCKED) evaluations."""
        completed = self.evaluations_passed + self.evaluations_warned + self.evaluations_blocked
        if completed == 0:
            return 0.0
        return self.total_evaluation_time_ms / completed

    @property
    def pass_rate(self) -> float:
        """Fraction of evaluations that passed (PASSED + WARNING) out of all outcomes."""
        outcomes = (
            self.evaluations_passed + self.evaluations_warned
            + self.evaluations_blocked + self.evaluations_overridden
        )
        if outcomes == 0:
            return 0.0
        return (self.evaluations_passed + self.evaluations_warned) / outcomes

    @property
    def block_rate(self) -> float:
        """Fraction of evaluations that were blocked out of all outcomes."""
        outcomes = (
            self.evaluations_passed + self.evaluations_warned
            + self.evaluations_blocked + self.evaluations_overridden
        )
        if outcomes == 0:
            return 0.0
        return self.evaluations_blocked / outcomes

    @property
    def override_rate(self) -> float:
        """Fraction of evaluations that were overridden out of all outcomes."""
        outcomes = (
            self.evaluations_passed + self.evaluations_warned
            + self.evaluations_blocked + self.evaluations_overridden
        )
        if outcomes == 0:
            return 0.0
        return self.evaluations_overridden / outcomes

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def touch(self) -> None:
        """Update the last_updated_at timestamp."""
        self.last_updated_at = time.time()

    def record_created(self) -> None:
        self.evaluations_created += 1
        self.touch()

    def record_passed(self, evaluation_time_ms: float = 0.0) -> None:
        self.evaluations_passed       += 1
        self.total_evaluation_time_ms += evaluation_time_ms
        self.touch()

    def record_warned(self, evaluation_time_ms: float = 0.0) -> None:
        self.evaluations_warned       += 1
        self.total_evaluation_time_ms += evaluation_time_ms
        self.touch()

    def record_blocked(self, evaluation_time_ms: float = 0.0) -> None:
        self.evaluations_blocked      += 1
        self.total_evaluation_time_ms += evaluation_time_ms
        self.touch()

    def record_overridden(self) -> None:
        self.evaluations_overridden += 1
        self.touch()

    def record_expired(self) -> None:
        self.evaluations_expired += 1
        self.touch()

    def record_failed(self) -> None:
        self.evaluations_failed += 1
        self.touch()

    def record_archived(self) -> None:
        self.evaluations_archived += 1
        self.touch()

    def record_transition(self, is_override: bool = False) -> None:
        self.total_transitions += 1
        if is_override:
            self.override_count += 1
        self.touch()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluations_created":        self.evaluations_created,
            "evaluations_passed":         self.evaluations_passed,
            "evaluations_warned":         self.evaluations_warned,
            "evaluations_blocked":        self.evaluations_blocked,
            "evaluations_overridden":     self.evaluations_overridden,
            "evaluations_expired":        self.evaluations_expired,
            "evaluations_failed":         self.evaluations_failed,
            "evaluations_archived":       self.evaluations_archived,
            "total_transitions":          self.total_transitions,
            "override_count":             self.override_count,
            "total_evaluation_time_ms":   self.total_evaluation_time_ms,
            "average_evaluation_time_ms": self.average_evaluation_time_ms,
            "pass_rate":                  self.pass_rate,
            "block_rate":                 self.block_rate,
            "override_rate":              self.override_rate,
            "last_updated_at":            self.last_updated_at,
        }
