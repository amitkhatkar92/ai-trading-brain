"""iios/execution/risk/controls/risk_control_statistics.py
==================================================
Statistics accumulators for the Controls Framework.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .constants import ControlAction


@dataclass
class ControlStatistics:
    """
    Mutable statistics accumulator for the Controls Framework.

    Thread-safety: callers must hold an external lock when calling
    ``record()`` concurrently.  The RiskControlManager does this.
    """

    # ── Counters per action ───────────────────────────────────────────────────
    allowed_count:        int = 0
    warning_count:        int = 0
    retry_count:          int = 0
    paused_count:         int = 0
    override_count:       int = 0
    cancel_count:         int = 0
    blocked_count:        int = 0
    emergency_count:      int = 0

    # ── Aggregate counters ────────────────────────────────────────────────────
    total_evaluations:    int   = 0
    total_time_ms:        float = 0.0
    min_time_ms:          float = float("inf")
    max_time_ms:          float = 0.0

    # ── Per-policy breakdown ──────────────────────────────────────────────────
    policy_counts:        dict = field(default_factory=dict)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def average_time_ms(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.total_time_ms / self.total_evaluations

    @property
    def block_rate(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.blocked_count / self.total_evaluations

    @property
    def override_rate(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.override_count / self.total_evaluations

    @property
    def emergency_rate(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.emergency_count / self.total_evaluations

    @property
    def allow_rate(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.allowed_count / self.total_evaluations

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record(self, elapsed_ms: float, action: ControlAction, policy_type: str = "") -> None:
        """Record a completed evaluation."""
        self.total_evaluations += 1
        self.total_time_ms     += elapsed_ms

        if elapsed_ms < self.min_time_ms:
            self.min_time_ms = elapsed_ms
        if elapsed_ms > self.max_time_ms:
            self.max_time_ms = elapsed_ms

        _counter_map = {
            ControlAction.ALLOW:              "allowed_count",
            ControlAction.ALLOW_WITH_WARNING: "warning_count",
            ControlAction.RETRY:              "retry_count",
            ControlAction.PAUSE:              "paused_count",
            ControlAction.REQUIRE_OVERRIDE:   "override_count",
            ControlAction.CANCEL:             "cancel_count",
            ControlAction.BLOCK:              "blocked_count",
            ControlAction.EMERGENCY_STOP:     "emergency_count",
        }
        attr = _counter_map.get(action)
        if attr:
            setattr(self, attr, getattr(self, attr) + 1)

        if policy_type:
            self.policy_counts[policy_type] = self.policy_counts.get(policy_type, 0) + 1

    def to_dict(self) -> dict:
        return {
            "allowed_count":    self.allowed_count,
            "warning_count":    self.warning_count,
            "retry_count":      self.retry_count,
            "paused_count":     self.paused_count,
            "override_count":   self.override_count,
            "cancel_count":     self.cancel_count,
            "blocked_count":    self.blocked_count,
            "emergency_count":  self.emergency_count,
            "total_evaluations": self.total_evaluations,
            "average_time_ms":  self.average_time_ms,
            "min_time_ms":      self.min_time_ms if self.total_evaluations else 0.0,
            "max_time_ms":      self.max_time_ms,
            "block_rate":       self.block_rate,
            "override_rate":    self.override_rate,
            "emergency_rate":   self.emergency_rate,
            "policy_counts":    dict(self.policy_counts),
        }
