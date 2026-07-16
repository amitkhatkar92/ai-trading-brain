"""iios/execution/positions/lifecycle/position_transition.py
==================================================
PositionTransition — immutable record of a single state-machine
transition for a trading position.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import PositionState, VALID_TRANSITIONS


@dataclass(frozen=True)
class PositionTransition:
    """
    Immutable record of a position state transition.

    Produced by ``Position.transition_to()`` and appended to
    ``PositionHistory``.  Never mutated after creation.
    """

    transition_id: str
    position_id:   str
    from_state:    PositionState
    to_state:      PositionState
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
        from .constants import TERMINAL_STATES
        return self.to_state in TERMINAL_STATES

    @property
    def is_recovery(self) -> bool:
        """True if this transition is part of a recovery sequence."""
        return self.to_state in {
            PositionState.RECOVERING,
            PositionState.RECOVERED,
        }

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "transition_id": self.transition_id,
            "position_id":   self.position_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "triggered_at":  self.triggered_at,
            "actor":         self.actor,
            "reason":        self.reason,
            "metadata":      dict(self.metadata),
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_transition(
    position_id: str,
    from_state:  PositionState,
    to_state:    PositionState,
    *,
    actor:    str = "",
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> PositionTransition:
    """Create a new ``PositionTransition`` with a fresh UUID and timestamp."""
    return PositionTransition(
        transition_id=str(uuid.uuid4()),
        position_id=position_id,
        from_state=from_state,
        to_state=to_state,
        triggered_at=time.time(),
        actor=actor,
        reason=reason,
        metadata=metadata or {},
    )
