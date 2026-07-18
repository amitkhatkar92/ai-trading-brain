"""
iios/execution/recovery/policies/recovery_priority.py
=====================================================
RecoveryPriorityEvaluator — computes the recovery priority from context.

The evaluator is stateless; it reads a PolicyEvaluationContext and returns
a PriorityScore detailing the final priority and the factors that drove it.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from .constants import (
    FailureCategory,
    FailureSeverity,
    PolicyPriority,
    SEVERITY_PRIORITY_MAP,
)


@dataclass(frozen=True)
class PriorityScore:
    """Result of priority evaluation."""

    base_priority:     PolicyPriority
    severity_boost:    int               # +N levels boosted by severity
    frequency_boost:   int               # +N levels boosted by failure frequency
    risk_boost:        int               # +N levels boosted by risk state
    final_priority:    PolicyPriority
    factors:           Tuple[str, ...]
    computed_at:       float             = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_priority":   self.base_priority.name,
            "severity_boost":  self.severity_boost,
            "frequency_boost": self.frequency_boost,
            "risk_boost":      self.risk_boost,
            "final_priority":  self.final_priority.name,
            "factors":         list(self.factors),
        }


# Ordered from lowest to highest for clamping
_PRIORITY_ORDER = [
    PolicyPriority.LOW,
    PolicyPriority.NORMAL,
    PolicyPriority.HIGH,
    PolicyPriority.CRITICAL,
    PolicyPriority.EMERGENCY,
]

_PRIORITY_TO_IDX = {p: i for i, p in enumerate(_PRIORITY_ORDER)}
_IDX_TO_PRIORITY = {i: p for i, p in enumerate(_PRIORITY_ORDER)}


def _boost(priority: PolicyPriority, amount: int) -> PolicyPriority:
    idx = min(_PRIORITY_TO_IDX[priority] + amount, len(_PRIORITY_ORDER) - 1)
    return _IDX_TO_PRIORITY[idx]


class RecoveryPriorityEvaluator:
    """
    Stateless evaluator that maps a PolicyEvaluationContext to a PriorityScore.

    Rules:
    1. Base priority from failure_severity (SEVERITY_PRIORITY_MAP).
    2. RISK_VIOLATION or !is_within_risk_limits → EMERGENCY immediately.
    3. failure_frequency > 5 → +1 level.
    4. recent_recovery_failed → +1 level.
    5. HIGH/CRITICAL severity with not is_subsystem_healthy → +1 level.
    6. Clamped at EMERGENCY.
    """

    def evaluate(self, context: "PolicyEvaluationContext") -> PriorityScore:  # type: ignore[name-defined]
        factors = []
        severity_boost   = 0
        frequency_boost  = 0
        risk_boost       = 0

        base = SEVERITY_PRIORITY_MAP.get(context.failure_severity, PolicyPriority.NORMAL)
        factors.append(f"severity={context.failure_severity.value} → {base.name}")

        # Rule 2 — risk critical overrides everything
        if (
            context.failure_category == FailureCategory.RISK_VIOLATION
            or not context.is_within_risk_limits
            or context.risk_level == "CRITICAL"
        ):
            factors.append("risk_critical → EMERGENCY")
            return PriorityScore(
                base_priority   = base,
                severity_boost  = 0,
                frequency_boost = 0,
                risk_boost      = 4,
                final_priority  = PolicyPriority.EMERGENCY,
                factors         = tuple(factors),
            )

        # Rule 3 — high failure frequency
        if context.failure_frequency > 5:
            frequency_boost += 1
            factors.append(f"failure_frequency={context.failure_frequency} > 5 → +1")

        # Rule 4 — previous recovery failed
        if context.recent_recovery_failed:
            frequency_boost += 1
            factors.append("recent_recovery_failed → +1")

        # Rule 5 — high/critical severity + subsystem unhealthy
        if (
            context.failure_severity in (FailureSeverity.HIGH, FailureSeverity.CRITICAL)
            and not context.is_subsystem_healthy
        ):
            severity_boost += 1
            factors.append("high_severity + subsystem_unhealthy → +1")

        boosted = _boost(base, severity_boost + frequency_boost + risk_boost)
        factors.append(f"final={boosted.name}")

        return PriorityScore(
            base_priority   = base,
            severity_boost  = severity_boost,
            frequency_boost = frequency_boost,
            risk_boost      = risk_boost,
            final_priority  = boosted,
            factors         = tuple(factors),
        )
