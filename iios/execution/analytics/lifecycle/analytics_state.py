"""
iios/execution/analytics/lifecycle/analytics_state.py
=====================================================
AnalyticsStateRecord — immutable record of a session entering a state.

Distinct from AnalyticsTransition (which records the edge); this records
the node (time-of-entry into a state).

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .constants import ACTOR_LIFECYCLE, VERSION, AnalyticsState


@dataclass(frozen=True)
class AnalyticsStateRecord:
    """
    Immutable record of an analytics session entering a particular state.

    Fields
    ------
    state:       The state entered.
    entered_at:  Wall-time of entry.
    actor:       Who triggered the entry.
    reason:      Optional human-readable context.
    version:     Framework version.
    """

    state:      AnalyticsState
    entered_at: float
    actor:      str = ACTOR_LIFECYCLE
    reason:     str = ""
    version:    str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state":      self.state.value,
            "entered_at": self.entered_at,
            "actor":      self.actor,
            "reason":     self.reason,
            "version":    self.version,
        }


def can_transition(
    from_state: AnalyticsState,
    to_state:   AnalyticsState,
) -> bool:
    """Return True iff the transition is allowed by the state machine."""
    from .constants import VALID_TRANSITIONS
    return to_state in VALID_TRANSITIONS.get(from_state, frozenset())
