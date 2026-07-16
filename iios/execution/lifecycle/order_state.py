"""iios/execution/lifecycle/order_state.py
==================================================
OrderState enumeration and the canonical state machine
transition table.

Every state transition attempted anywhere in the system
must pass through can_transition() before being applied.
Transitions not present in VALID_TRANSITIONS are INVALID
and will raise InvalidTransitionError at the registry
boundary.

State groups
------------
Initiation:    CREATED, VALIDATED
Submission:    PENDING_SUBMISSION, SUBMITTED, ACKNOWLEDGED
Active fill:   PARTIALLY_FILLED
Terminal:      FILLED
Cancellation:  CANCEL_PENDING, CANCELLED
Error:         REJECTED, EXPIRED, FAILED
Recovery:      RECOVERING, RECOVERED
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


class OrderState(str, Enum):
    """Canonical order lifecycle states."""
    CREATED            = "CREATED"
    VALIDATED          = "VALIDATED"
    PENDING_SUBMISSION = "PENDING_SUBMISSION"
    SUBMITTED          = "SUBMITTED"
    ACKNOWLEDGED       = "ACKNOWLEDGED"
    PARTIALLY_FILLED   = "PARTIALLY_FILLED"
    FILLED             = "FILLED"
    CANCEL_PENDING     = "CANCEL_PENDING"
    CANCELLED          = "CANCELLED"
    REJECTED           = "REJECTED"
    EXPIRED            = "EXPIRED"
    FAILED             = "FAILED"
    RECOVERING         = "RECOVERING"
    RECOVERED          = "RECOVERED"


# ── Canonical transition table ─────────────────────────────────────────────────
VALID_TRANSITIONS: Dict[OrderState, FrozenSet[OrderState]] = {
    OrderState.CREATED: frozenset({
        OrderState.VALIDATED,
        OrderState.REJECTED,
        OrderState.FAILED,
    }),
    OrderState.VALIDATED: frozenset({
        OrderState.PENDING_SUBMISSION,
        OrderState.REJECTED,
        OrderState.FAILED,
    }),
    OrderState.PENDING_SUBMISSION: frozenset({
        OrderState.SUBMITTED,
        OrderState.CANCELLED,   # cancelled before reaching broker
        OrderState.FAILED,
    }),
    OrderState.SUBMITTED: frozenset({
        OrderState.ACKNOWLEDGED,
        OrderState.REJECTED,
        OrderState.CANCEL_PENDING,
        OrderState.EXPIRED,
        OrderState.FAILED,
    }),
    OrderState.ACKNOWLEDGED: frozenset({
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.REJECTED,
        OrderState.EXPIRED,
        OrderState.FAILED,
    }),
    OrderState.PARTIALLY_FILLED: frozenset({
        OrderState.PARTIALLY_FILLED,   # another partial fill
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.CANCELLED,           # partial cancel confirmed
        OrderState.EXPIRED,
        OrderState.FAILED,
    }),
    OrderState.CANCEL_PENDING: frozenset({
        OrderState.CANCELLED,
        OrderState.ACKNOWLEDGED,        # cancel rejected — order still live
        OrderState.PARTIALLY_FILLED,    # filled during cancel race
        OrderState.FILLED,              # fully filled during cancel race
        OrderState.FAILED,
    }),
    # ── FILLED is the only permanently terminal state ──────────────────────
    OrderState.FILLED: frozenset(),
    # ── Error / cancellation states can enter recovery ─────────────────────
    OrderState.CANCELLED: frozenset({OrderState.RECOVERING}),
    OrderState.REJECTED:  frozenset({OrderState.RECOVERING}),
    OrderState.EXPIRED:   frozenset({OrderState.RECOVERING}),
    OrderState.FAILED:    frozenset({OrderState.RECOVERING}),
    # ── Recovery path ──────────────────────────────────────────────────────
    OrderState.RECOVERING: frozenset({
        OrderState.RECOVERED,
        OrderState.FAILED,
    }),
    OrderState.RECOVERED: frozenset({
        OrderState.PENDING_SUBMISSION,  # resubmission
        OrderState.CANCELLED,           # decision: do not resubmit
        OrderState.FAILED,
    }),
}

# ── Derived state sets ─────────────────────────────────────────────────────────

TERMINAL_STATES: FrozenSet[OrderState] = frozenset(
    s for s, targets in VALID_TRANSITIONS.items() if len(targets) == 0
)

ACTIVE_STATES: FrozenSet[OrderState] = frozenset({
    OrderState.PENDING_SUBMISSION,
    OrderState.SUBMITTED,
    OrderState.ACKNOWLEDGED,
    OrderState.PARTIALLY_FILLED,
    OrderState.CANCEL_PENDING,
})

CANCELLABLE_STATES: FrozenSet[OrderState] = frozenset({
    OrderState.SUBMITTED,
    OrderState.ACKNOWLEDGED,
    OrderState.PARTIALLY_FILLED,
})

RECOVERABLE_STATES: FrozenSet[OrderState] = frozenset({
    OrderState.CANCELLED,
    OrderState.REJECTED,
    OrderState.EXPIRED,
    OrderState.FAILED,
})

FILL_STATES: FrozenSet[OrderState] = frozenset({
    OrderState.PARTIALLY_FILLED,
    OrderState.FILLED,
})


# ── Helper functions ───────────────────────────────────────────────────────────

def can_transition(from_state: OrderState, to_state: OrderState) -> bool:
    """Return True iff the transition from_state → to_state is valid."""
    return to_state in VALID_TRANSITIONS.get(from_state, frozenset())


def allowed_next(state: OrderState) -> FrozenSet[OrderState]:
    """Return all states reachable in one step from *state*."""
    return VALID_TRANSITIONS.get(state, frozenset())


def is_terminal(state: OrderState) -> bool:
    """Return True iff *state* has no outgoing transitions."""
    return state in TERMINAL_STATES
