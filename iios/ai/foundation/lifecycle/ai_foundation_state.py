"""
ai_foundation_state.py — iios.ai.foundation.lifecycle
======================================================
Immutable state records and transition guard for the AI Foundation lifecycle.

A1 AI Foundation — Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_LIFECYCLE,
    SCHEMA_VERSION,
    VERSION,
    AILifecycleState,
    VALID_TRANSITIONS,
)


@dataclass(frozen=True)
class AIStateRecord:
    """
    Immutable record of a module entering a particular lifecycle state.

    One record is appended to state history each time a transition executes.

    Fields
    ------
    record_id :  Unique identifier for this state record.
    state :      The state the module entered.
    entered_at : Wall-clock time (``time.time()``) of entry.
    actor :      Identifier of the actor that triggered the transition.
    reason :     Optional human-readable context for the state entry.
    error :      Optional error message (for FAILED transitions).
    version :    Framework version string.
    schema :     Serialisation schema version.
    """
    state:      AILifecycleState
    entered_at: float
    actor:      str            = ACTOR_LIFECYCLE
    reason:     str            = ""
    error:      Optional[str]  = None
    record_id:  str            = ""
    version:    str            = VERSION
    schema:     str            = SCHEMA_VERSION

    def __post_init__(self) -> None:
        # Allow callers to omit record_id; generate one if blank
        if not self.record_id:
            object.__setattr__(self, "record_id", str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict for logging or persistence."""
        return {
            "record_id":  self.record_id,
            "state":      self.state.value,
            "entered_at": self.entered_at,
            "actor":      self.actor,
            "reason":     self.reason,
            "error":      self.error,
            "version":    self.version,
            "schema":     self.schema,
        }


@dataclass(frozen=True)
class AITransitionRecord:
    """
    Immutable record of a state transition (from → to).

    Stored in the module's transition history for audit and replay.
    """
    transition_id: str
    from_state:    AILifecycleState
    to_state:      AILifecycleState
    triggered_at:  float
    actor:         str
    success:       bool
    error:         Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "triggered_at":  self.triggered_at,
            "actor":         self.actor,
            "success":       self.success,
            "error":         self.error,
        }


def can_transition(
    from_state: AILifecycleState,
    to_state:   AILifecycleState,
) -> bool:
    """
    Return ``True`` iff the transition ``from_state → to_state`` is
    permitted by the AI lifecycle state machine.

    Parameters
    ----------
    from_state : Current state of the module.
    to_state :   Proposed next state.
    """
    return to_state in VALID_TRANSITIONS.get(from_state, frozenset())


def make_state_record(
    state:  AILifecycleState,
    *,
    actor:  str = ACTOR_LIFECYCLE,
    reason: str = "",
    error:  Optional[str] = None,
) -> AIStateRecord:
    """Convenience factory for :class:`AIStateRecord`."""
    return AIStateRecord(
        state      = state,
        entered_at = time.time(),
        actor      = actor,
        reason     = reason,
        error      = error,
        record_id  = str(uuid.uuid4()),
    )
