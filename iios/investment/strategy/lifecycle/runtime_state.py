"""iios/investment/strategy/lifecycle/runtime_state.py
Runtime engine state machine and point-in-time snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, FrozenSet, Optional


class RuntimeState(str, Enum):
    """Operational states of the StrategyLifecycleEngine."""

    IDLE         = "idle"           # constructed, not yet started
    INITIALIZING = "initializing"   # start() called, subsystems coming up
    RUNNING      = "running"        # accepting and executing strategies
    PAUSED       = "paused"         # execution suspended, queue preserved
    DRAINING     = "draining"       # stop() called, finishing in-flight work
    SHUTDOWN     = "shutdown"       # fully stopped

    def is_accepting(self) -> bool:
        """True if the engine accepts new strategy submissions."""
        return self == RuntimeState.RUNNING

    def is_terminal(self) -> bool:
        return self == RuntimeState.SHUTDOWN

    def can_pause(self) -> bool:
        return self == RuntimeState.RUNNING

    def can_resume(self) -> bool:
        return self == RuntimeState.PAUSED

    def can_stop(self) -> bool:
        return self in (
            RuntimeState.RUNNING,
            RuntimeState.PAUSED,
            RuntimeState.DRAINING,
        )


_RT_TRANSITIONS: Dict[RuntimeState, FrozenSet[RuntimeState]] = {
    RuntimeState.IDLE:         frozenset({RuntimeState.INITIALIZING, RuntimeState.SHUTDOWN}),
    RuntimeState.INITIALIZING: frozenset({RuntimeState.RUNNING, RuntimeState.SHUTDOWN}),
    RuntimeState.RUNNING:      frozenset({RuntimeState.PAUSED, RuntimeState.DRAINING, RuntimeState.SHUTDOWN}),
    RuntimeState.PAUSED:       frozenset({RuntimeState.RUNNING, RuntimeState.DRAINING, RuntimeState.SHUTDOWN}),
    RuntimeState.DRAINING:     frozenset({RuntimeState.SHUTDOWN}),
    RuntimeState.SHUTDOWN:     frozenset(),
}


def validate_runtime_transition(
    from_state: RuntimeState, to_state: RuntimeState
) -> bool:
    """Return True if the transition from_state → to_state is valid."""
    return to_state in _RT_TRANSITIONS.get(from_state, frozenset())


@dataclass
class RuntimeStateSnapshot:
    """Point-in-time view of engine state and key counters."""

    state: RuntimeState
    captured_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    active_strategies: int = 0
    queued_strategies: int = 0
    total_cycles: int = 0
    failed_cycles: int = 0
    uptime_seconds: float = 0.0
    paused_at: Optional[datetime] = None
    started_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.total_cycles == 0:
            return 1.0
        return (self.total_cycles - self.failed_cycles) / self.total_cycles

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "active_strategies": self.active_strategies,
            "queued_strategies": self.queued_strategies,
            "total_cycles": self.total_cycles,
            "failed_cycles": self.failed_cycles,
            "success_rate": round(self.success_rate, 4),
            "uptime_seconds": round(self.uptime_seconds, 1),
            "captured_at": self.captured_at.isoformat(),
        }
