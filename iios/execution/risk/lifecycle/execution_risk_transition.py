"""iios/execution/risk/lifecycle/execution_risk_transition.py
==================================================
RiskTransition — immutable record of a single state-machine
transition for an execution risk evaluation.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import RiskState, TERMINAL_STATES, VALID_TRANSITIONS


@dataclass(frozen=True)
class RiskTransition:
    """
    Immutable record of an execution risk evaluation state transition.

    Produced by ``ExecutionRisk.transition_to()`` and appended to
    ``RiskHistory``.  Never mutated after creation.
    """

    transition_id: str
    risk_id:       str
    from_state:    RiskState
    to_state:      RiskState
    triggered_at:  float
    actor:         str
    reason:        str
    metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_valid(self) -> bool:
        """True if this transition is permitted by the state machine."""
        return self.to_state in VALID_TRANSITIONS.get(self.from_state, frozenset())

    @property
    def is_terminal(self) -> bool:
        """True if the transition leads to a terminal state."""
        return self.to_state in TERMINAL_STATES

    @property
    def is_override(self) -> bool:
        """True if this transition leads to an OVERRIDDEN outcome."""
        return self.to_state == RiskState.OVERRIDDEN

    @property
    def is_block(self) -> bool:
        """True if this transition leads to a BLOCKED outcome."""
        return self.to_state == RiskState.BLOCKED

    @property
    def is_pass(self) -> bool:
        """True if this transition leads to a passing outcome (PASSED or WARNING)."""
        return self.to_state in {RiskState.PASSED, RiskState.WARNING}

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "transition_id": self.transition_id,
            "risk_id":       self.risk_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "triggered_at":  self.triggered_at,
            "actor":         self.actor,
            "reason":        self.reason,
            "metadata":      dict(self.metadata),
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_risk_transition(
    risk_id:    str,
    from_state: RiskState,
    to_state:   RiskState,
    *,
    actor:    str = "",
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> RiskTransition:
    """Create a new ``RiskTransition`` with a fresh UUID and timestamp."""
    return RiskTransition(
        transition_id=str(uuid.uuid4()),
        risk_id=risk_id,
        from_state=from_state,
        to_state=to_state,
        triggered_at=time.time(),
        actor=actor,
        reason=reason,
        metadata=metadata or {},
    )
