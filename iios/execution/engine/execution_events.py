"""iios/execution/engine/execution_events.py
==================================================
Events produced by the Execution Engine.

Each successful engine state transition produces an ExecutionEvent
that is dispatched to registered listeners.

Event mapping (state entered → event type)
------------------------------------------
VALIDATING  → ExecutionStarted
PREPARING   → ExecutionValidated
READY       → ExecutionPrepared
EXECUTING   → ExecutionReady
COMPLETED   → ExecutionCompleted
FAILED      → ExecutionFailed
CANCELLED   → ExecutionCancelled
WAITING     → (no dedicated event — informational only)

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from .execution_state import EngineExecutionState

if TYPE_CHECKING:
    from .execution_context import ExecutionContext
    from .execution_result import ExecutionResult
    from .execution_snapshot import ExecutionSnapshot


class ExecutionEventType(str, Enum):
    """Types of events emitted by the Execution Engine."""
    EXECUTION_STARTED   = "EXECUTION_STARTED"
    EXECUTION_VALIDATED = "EXECUTION_VALIDATED"
    EXECUTION_PREPARED  = "EXECUTION_PREPARED"
    EXECUTION_READY     = "EXECUTION_READY"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    EXECUTION_FAILED    = "EXECUTION_FAILED"
    EXECUTION_CANCELLED = "EXECUTION_CANCELLED"


# Canonical mapping: engine state entered → event type
_STATE_EVENT_MAP: dict[EngineExecutionState, Optional[ExecutionEventType]] = {
    EngineExecutionState.IDLE:       None,
    EngineExecutionState.VALIDATING: ExecutionEventType.EXECUTION_STARTED,
    EngineExecutionState.PREPARING:  ExecutionEventType.EXECUTION_VALIDATED,
    EngineExecutionState.READY:      ExecutionEventType.EXECUTION_PREPARED,
    EngineExecutionState.EXECUTING:  ExecutionEventType.EXECUTION_READY,
    EngineExecutionState.WAITING:    None,
    EngineExecutionState.COMPLETED:  ExecutionEventType.EXECUTION_COMPLETED,
    EngineExecutionState.FAILED:     ExecutionEventType.EXECUTION_FAILED,
    EngineExecutionState.CANCELLED:  ExecutionEventType.EXECUTION_CANCELLED,
}


def event_type_for_state(state: EngineExecutionState) -> Optional[ExecutionEventType]:
    """
    Return the ExecutionEventType for entering *state*, or None if no event
    is emitted for that state.
    """
    return _STATE_EVENT_MAP.get(state)


@dataclass(frozen=True)
class ExecutionEvent:
    """
    Immutable record of one execution engine event.

    Dispatched to registered listeners after every relevant state transition.

    Attributes
    ----------
    event_id      : Unique event identifier.
    execution_id  : The execution session this event belongs to.
    event_type    : The type of event.
    occurred_at   : Unix timestamp.
    state         : Engine execution state at event time.
    snapshot      : Optional execution snapshot attached to this event.
    result        : Optional execution result (set on COMPLETED/FAILED/CANCELLED).
    payload       : Arbitrary extra data.
    """
    event_id:     str               = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str               = ""
    event_type:   ExecutionEventType = ExecutionEventType.EXECUTION_STARTED
    occurred_at:  float             = field(default_factory=time.time)
    state:        EngineExecutionState = EngineExecutionState.IDLE

    snapshot:     "Optional[ExecutionSnapshot]" = None
    result:       "Optional[ExecutionResult]"   = None
    payload:      dict[str, Any]                = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "execution_id": self.execution_id,
            "event_type":   self.event_type.value,
            "occurred_at":  self.occurred_at,
            "state":        self.state.value,
            "snapshot":     self.snapshot.to_dict() if self.snapshot else None,
            "result":       self.result.to_dict() if self.result else None,
            "payload":      dict(self.payload),
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionEvent("
            f"type={self.event_type.value!r}, "
            f"execution_id={self.execution_id!r}, "
            f"state={self.state.value!r})"
        )


def make_execution_event(
    execution_id: str,
    event_type:   ExecutionEventType,
    *,
    state:        Optional[EngineExecutionState] = None,
    snapshot:     "Optional[ExecutionSnapshot]"  = None,
    result:       "Optional[ExecutionResult]"    = None,
    payload:      Optional[dict[str, Any]]       = None,
    occurred_at:  Optional[float]                = None,
) -> ExecutionEvent:
    """
    Create an ExecutionEvent.

    Parameters
    ----------
    execution_id : Owning execution session.
    event_type   : Type of event.
    state        : Engine state at event time (inferred from event_type if None).
    snapshot     : Optional snapshot to attach.
    result       : Optional result to attach.
    payload      : Arbitrary extra data.
    occurred_at  : Timestamp override (defaults to now).
    """
    resolved_state = state
    if resolved_state is None:
        # Reverse-look up from event type
        for s, et in _STATE_EVENT_MAP.items():
            if et == event_type:
                resolved_state = s
                break
        if resolved_state is None:
            resolved_state = EngineExecutionState.IDLE

    return ExecutionEvent(
        event_id     = str(uuid.uuid4()),
        execution_id = execution_id,
        event_type   = event_type,
        occurred_at  = occurred_at if occurred_at is not None else time.time(),
        state        = resolved_state,
        snapshot     = snapshot,
        result       = result,
        payload      = dict(payload) if payload else {},
    )
