"""iios/execution/risk/rules/rule_statistics.py
==================================================
Rule execution statistics — per-rule and framework-level aggregates.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RuleExecutionStatistics:
    """Mutable per-rule execution counter and timing aggregator."""

    rule_id:   str
    rule_name: str

    # Counters
    executions_total:  int = 0
    pass_count:        int = 0
    warning_count:     int = 0
    block_count:       int = 0
    override_count:    int = 0
    failure_count:     int = 0
    skip_count:        int = 0

    # Timing (ms)
    total_time_ms:  float = 0.0
    min_time_ms:    float = float("inf")
    max_time_ms:    float = 0.0

    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def average_time_ms(self) -> float:
        if self.executions_total == 0:
            return 0.0
        return self.total_time_ms / self.executions_total

    @property
    def pass_rate(self) -> float:
        if self.executions_total == 0:
            return 1.0
        return (self.pass_count + self.skip_count) / self.executions_total

    @property
    def block_rate(self) -> float:
        if self.executions_total == 0:
            return 0.0
        return self.block_count / self.executions_total

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record(self, elapsed_ms: float, outcome_str: str) -> None:
        self.executions_total += 1
        self.total_time_ms    += elapsed_ms
        if elapsed_ms < self.min_time_ms:
            self.min_time_ms = elapsed_ms
        if elapsed_ms > self.max_time_ms:
            self.max_time_ms = elapsed_ms
        self.last_updated_at = time.time()

        outcome_str = outcome_str.upper()
        if outcome_str == "PASS":
            self.pass_count     += 1
        elif outcome_str == "WARNING":
            self.warning_count  += 1
        elif outcome_str == "BLOCK":
            self.block_count    += 1
        elif outcome_str == "OVERRIDE_REQUIRED":
            self.override_count += 1
        elif outcome_str == "FAILED":
            self.failure_count  += 1
        elif outcome_str == "SKIPPED":
            self.skip_count     += 1

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":          self.rule_id,
            "rule_name":        self.rule_name,
            "executions_total": self.executions_total,
            "pass_count":       self.pass_count,
            "warning_count":    self.warning_count,
            "block_count":      self.block_count,
            "override_count":   self.override_count,
            "failure_count":    self.failure_count,
            "skip_count":       self.skip_count,
            "total_time_ms":    self.total_time_ms,
            "min_time_ms":      self.min_time_ms if self.executions_total > 0 else 0.0,
            "max_time_ms":      self.max_time_ms,
            "average_time_ms":  self.average_time_ms,
            "pass_rate":        self.pass_rate,
            "block_rate":       self.block_rate,
            "last_updated_at":  self.last_updated_at,
        }


@dataclass
class FrameworkStatistics:
    """Aggregate statistics across all rules in the framework."""

    # Aggregate counters
    total_evaluations:  int = 0
    total_rule_runs:    int = 0
    total_passed:       int = 0
    total_warned:       int = 0
    total_blocked:      int = 0
    total_overrides:    int = 0
    total_failures:     int = 0
    total_skipped:      int = 0

    # Timing
    total_time_ms:  float = 0.0

    # Per-rule breakdown
    per_rule: Dict[str, RuleExecutionStatistics] = field(default_factory=dict)

    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def average_time_ms(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.total_time_ms / self.total_evaluations

    @property
    def slowest_rule(self) -> Optional[str]:
        if not self.per_rule:
            return None
        return max(self.per_rule, key=lambda k: self.per_rule[k].max_time_ms)

    @property
    def fastest_rule(self) -> Optional[str]:
        if not self.per_rule:
            return None
        return min(self.per_rule, key=lambda k: self.per_rule[k].average_time_ms
                   if self.per_rule[k].executions_total > 0 else float("inf"))

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_evaluation_started(self) -> None:
        self.total_evaluations += 1
        self.last_updated_at    = time.time()

    def record_rule_result(self, rule_id: str, rule_name: str, elapsed_ms: float, outcome_str: str) -> None:
        self.total_rule_runs += 1
        self.total_time_ms   += elapsed_ms
        self.last_updated_at  = time.time()

        outcome_str = outcome_str.upper()
        if outcome_str == "PASS":
            self.total_passed   += 1
        elif outcome_str == "WARNING":
            self.total_warned   += 1
        elif outcome_str == "BLOCK":
            self.total_blocked  += 1
        elif outcome_str == "OVERRIDE_REQUIRED":
            self.total_overrides += 1
        elif outcome_str == "FAILED":
            self.total_failures += 1
        elif outcome_str == "SKIPPED":
            self.total_skipped  += 1

        if rule_id not in self.per_rule:
            self.per_rule[rule_id] = RuleExecutionStatistics(
                rule_id=rule_id, rule_name=rule_name
            )
        self.per_rule[rule_id].record(elapsed_ms, outcome_str)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self.total_evaluations,
            "total_rule_runs":   self.total_rule_runs,
            "total_passed":      self.total_passed,
            "total_warned":      self.total_warned,
            "total_blocked":     self.total_blocked,
            "total_overrides":   self.total_overrides,
            "total_failures":    self.total_failures,
            "total_skipped":     self.total_skipped,
            "total_time_ms":     self.total_time_ms,
            "average_time_ms":   self.average_time_ms,
            "slowest_rule":      self.slowest_rule,
            "fastest_rule":      self.fastest_rule,
            "per_rule":          {k: v.to_dict() for k, v in self.per_rule.items()},
            "last_updated_at":   self.last_updated_at,
        }
