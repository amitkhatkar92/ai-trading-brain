"""
portfolio_transition.py — iios.portfolio.lifecycle
====================================================
Immutable record of a portfolio session state transition.

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import ACTOR_LIFECYCLE, VERSION, PortfolioState


@dataclass(frozen=True)
class PortfolioTransition:
    """
    Immutable record of a single state transition in a portfolio session.

    One :class:`PortfolioTransition` is appended to the session's
    ``transitions`` list each time the session moves from one state to another.

    Fields
    ------
    transition_id :   Unique identifier for this transition record.
    session_id :      Portfolio session that was transitioned.
    from_state :      State the session was in before the transition.
    to_state :        State the session entered after the transition.
    actor :           Identifier of the actor that triggered the transition.
    reason :          Optional human-readable context.
    transitioned_at : Wall-clock time (``time.time()``) of the transition.
    metadata :        Optional supplementary transition data.
    version :         Framework version string.
    """
    transition_id:    str
    session_id:       str
    from_state:       PortfolioState
    to_state:         PortfolioState
    actor:            str            = ACTOR_LIFECYCLE
    reason:           str            = ""
    transitioned_at:  float          = field(default_factory=time.time)
    metadata:         Dict[str, Any] = field(default_factory=dict)
    version:          str            = VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for logging or persistence."""
        return {
            "transition_id":   self.transition_id,
            "session_id":      self.session_id,
            "from_state":      self.from_state.value,
            "to_state":        self.to_state.value,
            "actor":           self.actor,
            "reason":          self.reason,
            "transitioned_at": self.transitioned_at,
            "version":         self.version,
        }


def make_transition(
    session_id: str,
    from_state: PortfolioState,
    to_state:   PortfolioState,
    *,
    actor:    str = ACTOR_LIFECYCLE,
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> PortfolioTransition:
    """
    Convenience constructor for :class:`PortfolioTransition`.

    Assigns a new UUID ``transition_id`` and the current timestamp.
    """
    return PortfolioTransition(
        transition_id   = str(uuid.uuid4()),
        session_id      = session_id,
        from_state      = from_state,
        to_state        = to_state,
        actor           = actor,
        reason          = reason,
        metadata        = dict(metadata or {}),
    )
