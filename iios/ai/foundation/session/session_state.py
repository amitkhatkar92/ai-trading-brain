"""
session_state.py -- iios.ai.foundation.session
================================================
SessionState enumeration and valid-transition table for AI sessions.

An AI session is a bounded context for one agent invocation or
conversational turn.  Its lifecycle is distinct from the module's
AILifecycleState (which tracks process-level operational state).

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


class SessionState(str, Enum):
    """
    Operational states of an :class:`AISession`.

    States
    ------
    PENDING    -- created but not yet active (pre-start)
    ACTIVE     -- currently processing work
    SUSPENDED  -- paused; can be resumed
    COMPLETED  -- finished successfully
    EXPIRED    -- TTL elapsed before completion
    CANCELLED  -- explicitly cancelled by the caller
    FAILED     -- terminated due to an unrecoverable error
    """
    PENDING   = "pending"
    ACTIVE    = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    EXPIRED   = "expired"
    CANCELLED = "cancelled"
    FAILED    = "failed"


# Terminal states -- no further transitions allowed
TERMINAL_SESSION_STATES: FrozenSet[SessionState] = frozenset({
    SessionState.COMPLETED,
    SessionState.EXPIRED,
    SessionState.CANCELLED,
    SessionState.FAILED,
})

# States where new work may be submitted
ACTIVE_SESSION_STATES: FrozenSet[SessionState] = frozenset({
    SessionState.ACTIVE,
})

# Valid state transitions
VALID_SESSION_TRANSITIONS: Dict[SessionState, FrozenSet[SessionState]] = {
    SessionState.PENDING:   frozenset({SessionState.ACTIVE, SessionState.CANCELLED}),
    SessionState.ACTIVE:    frozenset({
        SessionState.SUSPENDED, SessionState.COMPLETED,
        SessionState.CANCELLED, SessionState.FAILED, SessionState.EXPIRED,
    }),
    SessionState.SUSPENDED: frozenset({SessionState.ACTIVE, SessionState.CANCELLED}),
    SessionState.COMPLETED: frozenset(),
    SessionState.EXPIRED:   frozenset(),
    SessionState.CANCELLED: frozenset(),
    SessionState.FAILED:    frozenset(),
}


def can_session_transition(from_state: SessionState, to_state: SessionState) -> bool:
    """Return ``True`` iff the transition ``from_state -> to_state`` is valid."""
    return to_state in VALID_SESSION_TRANSITIONS.get(from_state, frozenset())
