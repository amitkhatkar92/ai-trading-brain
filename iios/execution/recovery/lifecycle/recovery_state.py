"""iios/execution/recovery/lifecycle/recovery_state.py
==================================================
RecoveryStateRecord — immutable record of a session being in a
particular state at a particular time.

Distinct from RecoveryTransition (which records the edge); this records
the node (time-of-entry into a state).

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import RecoveryState, VERSION


@dataclass(frozen=True)
class RecoveryStateRecord:
    """
    Immutable record of a recovery session entering a particular state.

    Fields
    ------
    state:       The state entered.
    entered_at:  Wall-time of entry.
    actor:       Who triggered the entry.
    reason:      Optional human-readable context.
    version:     Framework version.
    """

    state:      RecoveryState
    entered_at: float
    actor:      str             = "iios:execution:recovery:lifecycle"
    reason:     str             = ""
    version:    str             = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state":      self.state.value,
            "entered_at": self.entered_at,
            "actor":      self.actor,
            "reason":     self.reason,
            "version":    self.version,
        }


def can_transition(from_state: RecoveryState, to_state: RecoveryState) -> bool:
    """Return True iff the transition is allowed by the state machine."""
    from .constants import VALID_TRANSITIONS
    return to_state in VALID_TRANSITIONS.get(from_state, frozenset())
