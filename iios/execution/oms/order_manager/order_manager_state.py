"""iios/execution/oms/order_manager/order_manager_state.py
==================================================
ManagedOrderState — the OMS-level state machine for a single
managed order, distinct from the M1 OrderState.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

from iios.execution.oms.order_manager.constants import (
    ManagerOrderState,
    TERMINAL_MANAGER_STATES,
    VALID_MANAGER_TRANSITIONS,
)
from iios.execution.oms.order_manager.exceptions import OrderManagerStateError


def can_manager_transition(
    current: ManagerOrderState,
    target:  ManagerOrderState,
) -> bool:
    """Return True if the OMS transition current → target is valid."""
    return target in VALID_MANAGER_TRANSITIONS.get(current, frozenset())


def assert_manager_transition(
    order_id: str,
    current:  ManagerOrderState,
    target:   ManagerOrderState,
) -> None:
    """Raise OrderManagerStateError if the transition is invalid."""
    if not can_manager_transition(current, target):
        raise OrderManagerStateError(
            order_id,
            current.value,
            target.value,
        )


def is_terminal(state: ManagerOrderState) -> bool:
    """Return True if the given OMS state is terminal."""
    return state in TERMINAL_MANAGER_STATES


def allowed_next(state: ManagerOrderState) -> frozenset[ManagerOrderState]:
    """Return the set of valid next states from *state*."""
    return VALID_MANAGER_TRANSITIONS.get(state, frozenset())
