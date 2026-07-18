"""
iios/execution/analytics/lifecycle/analytics_transition.py
==========================================================
AnalyticsTransition — immutable record of a single state-machine hop.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import ACTOR_LIFECYCLE, VERSION, AnalyticsState


@dataclass(frozen=True)
class AnalyticsTransition:
    """
    Immutable record of a single analytics state transition.

    One record is appended to the session's transition history for every
    successful ``transition_to()`` call.

    Fields
    ------
    transition_id: Globally unique transition ID.
    session_id:    Owning analytics session.
    from_state:    State before the transition.
    to_state:      State after the transition.
    actor:         Who / what triggered the transition.
    reason:        Human-readable context.
    occurred_at:   Wall-time of the transition.
    version:       Framework version.
    """

    transition_id: str
    session_id:    str
    from_state:    AnalyticsState
    to_state:      AnalyticsState
    actor:         str
    reason:        str
    occurred_at:   float
    version:       str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "session_id":    self.session_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "actor":         self.actor,
            "reason":        self.reason,
            "occurred_at":   self.occurred_at,
            "version":       self.version,
        }


def make_analytics_transition(
    session_id: str,
    from_state: AnalyticsState,
    to_state:   AnalyticsState,
    *,
    actor:         str           = ACTOR_LIFECYCLE,
    reason:        str           = "",
    transition_id: Optional[str] = None,
) -> AnalyticsTransition:
    """Factory for AnalyticsTransition."""
    return AnalyticsTransition(
        transition_id = transition_id or str(uuid.uuid4()),
        session_id    = session_id,
        from_state    = from_state,
        to_state      = to_state,
        actor         = actor,
        reason        = reason,
        occurred_at   = time.time(),
    )
