"""iios/investment/company/opportunity/opportunity_lifecycle.py
Lifecycle state definitions, valid transitions, and state-determination logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Set

from iios.investment.company.opportunity.opportunity_profile import OpportunityLifecycle


# ── Valid state transitions ────────────────────────────────────────────────────

_VALID_TRANSITIONS: Dict[OpportunityLifecycle, Set[OpportunityLifecycle]] = {
    OpportunityLifecycle.DISCOVERED: {
        OpportunityLifecycle.EMERGING,
        OpportunityLifecycle.MONITORING,
        OpportunityLifecycle.EXPIRED,
    },
    OpportunityLifecycle.EMERGING: {
        OpportunityLifecycle.HIGH_CONVICTION,
        OpportunityLifecycle.MONITORING,
        OpportunityLifecycle.WEAKENING,
        OpportunityLifecycle.EXPIRED,
    },
    OpportunityLifecycle.HIGH_CONVICTION: {
        OpportunityLifecycle.CONFIRMED,
        OpportunityLifecycle.MONITORING,
        OpportunityLifecycle.WEAKENING,
    },
    OpportunityLifecycle.CONFIRMED: {
        OpportunityLifecycle.MONITORING,
        OpportunityLifecycle.WEAKENING,
    },
    OpportunityLifecycle.MONITORING: {
        OpportunityLifecycle.EMERGING,
        OpportunityLifecycle.HIGH_CONVICTION,
        OpportunityLifecycle.WEAKENING,
        OpportunityLifecycle.EXPIRED,
    },
    OpportunityLifecycle.WEAKENING: {
        OpportunityLifecycle.MONITORING,
        OpportunityLifecycle.EXPIRED,
        OpportunityLifecycle.ARCHIVED,
    },
    OpportunityLifecycle.EXPIRED: {
        OpportunityLifecycle.DISCOVERED,   # re-discovery
        OpportunityLifecycle.ARCHIVED,
    },
    OpportunityLifecycle.ARCHIVED: set(),  # terminal
}

_ACTIVE_STATES: Set[OpportunityLifecycle] = {
    OpportunityLifecycle.DISCOVERED,
    OpportunityLifecycle.EMERGING,
    OpportunityLifecycle.HIGH_CONVICTION,
    OpportunityLifecycle.CONFIRMED,
    OpportunityLifecycle.MONITORING,
    OpportunityLifecycle.WEAKENING,
}

_HIGH_VALUE_STATES: Set[OpportunityLifecycle] = {
    OpportunityLifecycle.HIGH_CONVICTION,
    OpportunityLifecycle.CONFIRMED,
}


def is_valid_transition(
    current: OpportunityLifecycle,
    target: OpportunityLifecycle,
) -> bool:
    """Return True if the *current* → *target* transition is permitted."""
    return target in _VALID_TRANSITIONS.get(current, set())


def is_active(state: OpportunityLifecycle) -> bool:
    return state in _ACTIVE_STATES


def is_high_value(state: OpportunityLifecycle) -> bool:
    return state in _HIGH_VALUE_STATES


def determine_lifecycle(
    score: float,
    confidence: float,
    current: OpportunityLifecycle,
    evaluation_count: int,
    score_trend: float,          # positive = improving, negative = deteriorating
) -> OpportunityLifecycle:
    """
    Determine the appropriate lifecycle state from evaluation metrics.

    Rules (in priority order):
    1. ARCHIVED is terminal — never leave it automatically.
    2. Score < 30 OR confidence < 0.25 → EXPIRED (or ARCHIVED if already expired).
    3. Score ≥ 68 AND confidence ≥ 0.60:
       - If evaluation_count ≥ 3 and stable/improving → CONFIRMED
       - Else → HIGH_CONVICTION
    4. Score 52-67 AND confidence ≥ 0.45:
       - If score_trend > 0 → EMERGING
       - If current in high-value and score_trend < -5 → WEAKENING
       - Else → MONITORING
    5. Score 35-51:
       - If evaluation_count == 1 → DISCOVERED
       - If declining from high → WEAKENING
       - Else → MONITORING
    6. Score < 35 → EXPIRED / WEAKENING from high-value
    """
    if current == OpportunityLifecycle.ARCHIVED:
        return OpportunityLifecycle.ARCHIVED

    # Expired threshold
    if score < 30 or confidence < 0.25:
        if current == OpportunityLifecycle.EXPIRED:
            return OpportunityLifecycle.EXPIRED
        if is_high_value(current):
            return OpportunityLifecycle.WEAKENING
        return OpportunityLifecycle.EXPIRED

    # High conviction band
    if score >= 68 and confidence >= 0.60:
        if (
            evaluation_count >= 3
            and current in (
                OpportunityLifecycle.HIGH_CONVICTION,
                OpportunityLifecycle.CONFIRMED,
            )
            and score_trend >= -3.0
        ):
            return OpportunityLifecycle.CONFIRMED
        return OpportunityLifecycle.HIGH_CONVICTION

    # Moderate band
    if score >= 52 and confidence >= 0.45:
        if is_high_value(current) and score_trend < -5.0:
            return OpportunityLifecycle.WEAKENING
        if score_trend > 2.0:
            return OpportunityLifecycle.EMERGING
        return OpportunityLifecycle.MONITORING

    # Weak band
    if score >= 35:
        if evaluation_count <= 1:
            return OpportunityLifecycle.DISCOVERED
        if is_high_value(current) and score_trend < -3.0:
            return OpportunityLifecycle.WEAKENING
        return OpportunityLifecycle.MONITORING

    # Sub-threshold
    if is_high_value(current) or current == OpportunityLifecycle.CONFIRMED:
        return OpportunityLifecycle.WEAKENING
    return OpportunityLifecycle.EXPIRED


# ── Lifecycle change record ───────────────────────────────────────────────────

@dataclass
class LifecycleChange:
    """Records a single lifecycle state transition."""
    from_state: OpportunityLifecycle
    to_state:   OpportunityLifecycle
    score_at_change: float
    changed_at:  datetime
    reason:      str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_state":      self.from_state.value,
            "to_state":        self.to_state.value,
            "score_at_change": round(self.score_at_change, 2),
            "changed_at":      self.changed_at.isoformat(),
            "reason":          self.reason,
        }
