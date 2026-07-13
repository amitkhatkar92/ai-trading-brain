"""iios/investment/strategy/core/strategy_state.py
Institutional strategy lifecycle states and valid transition graph.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


class StrategyState(str, Enum):
    """All valid lifecycle states for an institutional strategy instance."""
    REGISTERED  = "registered"
    LOADED      = "loaded"
    INITIALIZED = "initialized"
    READY       = "ready"
    RUNNING     = "running"
    PAUSED      = "paused"
    COMPLETED   = "completed"
    FAILED      = "failed"
    ARCHIVED    = "archived"

    def is_terminal(self) -> bool:
        return self in _TERMINAL_STATES

    def is_active(self) -> bool:
        return self in _ACTIVE_STATES

    def can_run(self) -> bool:
        return self in _RUNNABLE_STATES


_TERMINAL_STATES: FrozenSet[StrategyState] = frozenset({
    StrategyState.COMPLETED,
    StrategyState.FAILED,
    StrategyState.ARCHIVED,
})

_ACTIVE_STATES: FrozenSet[StrategyState] = frozenset({
    StrategyState.RUNNING,
    StrategyState.PAUSED,
})

_RUNNABLE_STATES: FrozenSet[StrategyState] = frozenset({
    StrategyState.READY,
    StrategyState.PAUSED,
})

# Valid state transitions: state → set of allowed next states
STATE_TRANSITIONS: Dict[StrategyState, FrozenSet[StrategyState]] = {
    StrategyState.REGISTERED:  frozenset({StrategyState.LOADED, StrategyState.FAILED}),
    StrategyState.LOADED:      frozenset({StrategyState.INITIALIZED, StrategyState.FAILED, StrategyState.REGISTERED}),
    StrategyState.INITIALIZED: frozenset({StrategyState.READY, StrategyState.FAILED, StrategyState.LOADED}),
    StrategyState.READY:       frozenset({StrategyState.RUNNING, StrategyState.PAUSED, StrategyState.COMPLETED, StrategyState.FAILED, StrategyState.ARCHIVED}),
    StrategyState.RUNNING:     frozenset({StrategyState.READY, StrategyState.PAUSED, StrategyState.COMPLETED, StrategyState.FAILED}),
    StrategyState.PAUSED:      frozenset({StrategyState.RUNNING, StrategyState.READY, StrategyState.COMPLETED, StrategyState.FAILED}),
    StrategyState.COMPLETED:   frozenset({StrategyState.ARCHIVED, StrategyState.READY}),
    StrategyState.FAILED:      frozenset({StrategyState.ARCHIVED, StrategyState.LOADED}),
    StrategyState.ARCHIVED:    frozenset(),
}


def validate_transition(current: StrategyState, target: StrategyState) -> bool:
    """Return True if transitioning from current → target is valid."""
    return target in STATE_TRANSITIONS.get(current, frozenset())
