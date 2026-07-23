"""
supervisor_state.py — iios.supervisor.lifecycle
================================================
Immutable state-entry record and transition guard.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .constants import (
    ACTOR_LIFECYCLE,
    VERSION,
    SupervisorState,
    VALID_TRANSITIONS,
)


@dataclass(frozen=True)
class SupervisorStateRecord:
    """
    Immutable record of a supervisor session entering a particular state.

    One record is appended to the session's ``state_history`` each time a
    transition is executed.

    Fields
    ------
    state :      The state the session entered.
    entered_at : Wall-clock time (``time.time()``) of entry.
    actor :      Identifier of the actor that triggered the transition.
    reason :     Optional human-readable context for the state entry.
    version :    Framework version string.
    """
    state:      SupervisorState
    entered_at: float
    actor:      str = ACTOR_LIFECYCLE
    reason:     str = ""
    version:    str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for logging or persistence."""
        return {
            "state":      self.state.value,
            "entered_at": self.entered_at,
            "actor":      self.actor,
            "reason":     self.reason,
            "version":    self.version,
        }


def can_transition(
    from_state: SupervisorState,
    to_state:   SupervisorState,
) -> bool:
    """
    Return ``True`` iff the transition ``from_state \u2192 to_state`` is
    permitted by the institutional supervisor state machine.

    Parameters
    ----------
    from_state : Current state of the session.
    to_state :   Proposed next state.
    """
    return to_state in VALID_TRANSITIONS.get(from_state, frozenset())
