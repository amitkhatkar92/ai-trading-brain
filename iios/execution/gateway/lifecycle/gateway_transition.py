"""iios/execution/gateway/lifecycle/gateway_transition.py
==================================================
GatewayTransition — immutable record of a single state-machine
transition for an execution gateway request.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import GatewayState, TERMINAL_STATES, VALID_TRANSITIONS


@dataclass(frozen=True)
class GatewayTransition:
    """
    Immutable record of a gateway request state transition.

    Produced by ``GatewayRequest.transition_to()`` and appended to
    ``GatewayHistory``.  Never mutated after creation.
    """

    transition_id: str
    gateway_id:    str
    from_state:    GatewayState
    to_state:      GatewayState
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
        """True if the transition leads to a terminal state (ARCHIVED)."""
        return self.to_state in TERMINAL_STATES

    @property
    def is_success(self) -> bool:
        """True if this transition leads to COMPLETED."""
        return self.to_state == GatewayState.COMPLETED

    @property
    def is_failure(self) -> bool:
        """True if this transition leads to FAILED."""
        return self.to_state == GatewayState.FAILED

    @property
    def is_cancellation(self) -> bool:
        """True if this transition leads to CANCELLED."""
        return self.to_state == GatewayState.CANCELLED

    @property
    def is_dispatch(self) -> bool:
        """True if this transition leads to DISPATCHED."""
        return self.to_state == GatewayState.DISPATCHED

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "transition_id": self.transition_id,
            "gateway_id":    self.gateway_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "triggered_at":  self.triggered_at,
            "actor":         self.actor,
            "reason":        self.reason,
            "metadata":      dict(self.metadata),
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_gateway_transition(
    gateway_id: str,
    from_state: GatewayState,
    to_state:   GatewayState,
    *,
    actor:    str                     = "",
    reason:   str                     = "",
    metadata: Dict[str, Any] | None   = None,
) -> GatewayTransition:
    """Create a new ``GatewayTransition`` with a fresh UUID and timestamp."""
    return GatewayTransition(
        transition_id=str(uuid.uuid4()),
        gateway_id=gateway_id,
        from_state=from_state,
        to_state=to_state,
        triggered_at=time.time(),
        actor=actor,
        reason=reason,
        metadata=metadata or {},
    )
