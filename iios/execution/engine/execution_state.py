"""iios/execution/engine/execution_state.py
==================================================
Per-execution state machine for the IIOS Execution Engine.

States
------
IDLE          Initial state; not yet processing.
VALIDATING    Request and order are being validated.
PREPARING     ExecutionContext is being assembled.
READY         Context is ready; awaiting execution slot.
EXECUTING     Execution logic is running.
WAITING       Awaiting an external signal (e.g. broker ACK).
COMPLETED     Execution finished successfully.
FAILED        Execution failed; no recovery path at this level.
CANCELLED     Execution was cancelled before completion.

COMPLETED, FAILED, and CANCELLED are terminal — no further transitions.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet

from .exceptions import ExecutionStateError


class EngineExecutionState(str, Enum):
    """Per-execution lifecycle state inside the Execution Engine."""
    IDLE       = "IDLE"
    VALIDATING = "VALIDATING"
    PREPARING  = "PREPARING"
    READY      = "READY"
    EXECUTING  = "EXECUTING"
    WAITING    = "WAITING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"


# Canonical transition table
VALID_ENGINE_TRANSITIONS: dict[EngineExecutionState, FrozenSet[EngineExecutionState]] = {
    EngineExecutionState.IDLE:       frozenset({EngineExecutionState.VALIDATING,
                                                EngineExecutionState.CANCELLED}),
    EngineExecutionState.VALIDATING: frozenset({EngineExecutionState.PREPARING,
                                                EngineExecutionState.FAILED,
                                                EngineExecutionState.CANCELLED}),
    EngineExecutionState.PREPARING:  frozenset({EngineExecutionState.READY,
                                                EngineExecutionState.FAILED,
                                                EngineExecutionState.CANCELLED}),
    EngineExecutionState.READY:      frozenset({EngineExecutionState.EXECUTING,
                                                EngineExecutionState.CANCELLED}),
    EngineExecutionState.EXECUTING:  frozenset({EngineExecutionState.WAITING,
                                                EngineExecutionState.COMPLETED,
                                                EngineExecutionState.FAILED,
                                                EngineExecutionState.CANCELLED}),
    EngineExecutionState.WAITING:    frozenset({EngineExecutionState.EXECUTING,
                                                EngineExecutionState.COMPLETED,
                                                EngineExecutionState.FAILED,
                                                EngineExecutionState.CANCELLED}),
    EngineExecutionState.COMPLETED:  frozenset(),   # terminal
    EngineExecutionState.FAILED:     frozenset(),   # terminal
    EngineExecutionState.CANCELLED:  frozenset(),   # terminal
}

# Derived state sets
TERMINAL_ENGINE_STATES: FrozenSet[EngineExecutionState] = frozenset({
    EngineExecutionState.COMPLETED,
    EngineExecutionState.FAILED,
    EngineExecutionState.CANCELLED,
})

ACTIVE_ENGINE_STATES: FrozenSet[EngineExecutionState] = frozenset({
    EngineExecutionState.VALIDATING,
    EngineExecutionState.PREPARING,
    EngineExecutionState.READY,
    EngineExecutionState.EXECUTING,
    EngineExecutionState.WAITING,
})

CANCELLABLE_ENGINE_STATES: FrozenSet[EngineExecutionState] = frozenset(
    s for s, targets in VALID_ENGINE_TRANSITIONS.items()
    if EngineExecutionState.CANCELLED in targets
)


# ── Helper functions ──────────────────────────────────────────────────────────

def can_engine_transition(
    from_state: EngineExecutionState,
    to_state:   EngineExecutionState,
) -> bool:
    """Return True if *from_state* → *to_state* is a valid engine transition."""
    return to_state in VALID_ENGINE_TRANSITIONS.get(from_state, frozenset())


def allowed_engine_next(state: EngineExecutionState) -> FrozenSet[EngineExecutionState]:
    """Return the set of states reachable from *state*."""
    return VALID_ENGINE_TRANSITIONS.get(state, frozenset())


def is_engine_terminal(state: EngineExecutionState) -> bool:
    """Return True if *state* is a terminal engine state."""
    return state in TERMINAL_ENGINE_STATES


def assert_engine_transition(
    from_state:   EngineExecutionState,
    to_state:     EngineExecutionState,
    execution_id: str = "",
) -> None:
    """
    Raise ExecutionStateError if the transition is not valid.

    Parameters
    ----------
    from_state    : Current state.
    to_state      : Requested target state.
    execution_id  : Optional execution ID for error context.
    """
    if not can_engine_transition(from_state, to_state):
        raise ExecutionStateError(
            from_state.value,
            to_state.value,
            execution_id,
        )
