"""
knowledge_transition.py — iios.knowledge.lifecycle
----------------------------------------------------
Immutable lifecycle transition record.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import KnowledgeLifecycleState


@dataclass(frozen=True)
class KnowledgeTransition:
    """
    Immutable record of a single lifecycle state transition.

    One :class:`KnowledgeTransition` is created each time a knowledge session
    moves from one state to another.

    Fields
    ------
    transition_id : Unique identifier for this transition.
    session_id :    Owning knowledge session.
    from_state :    State before the transition.
    to_state :      State after the transition.
    actor :         Identity that triggered the transition.
    reason :        Optional context or failure reason.
    occurred_at :   Wall-clock time the transition occurred.
    duration_ms :   Time spent in ``from_state`` before this transition (ms).
    metadata :      Supplementary key-value metadata.
    """
    transition_id: str
    session_id:    str
    from_state:    KnowledgeLifecycleState
    to_state:      KnowledgeLifecycleState
    actor:         str
    reason:        str           = ""
    occurred_at:   float         = field(default_factory=time.time)
    duration_ms:   float         = 0.0
    metadata:      Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id:    str,
        from_state:    KnowledgeLifecycleState,
        to_state:      KnowledgeLifecycleState,
        actor:         str,
        *,
        transition_id: Optional[str]            = None,
        reason:        str                      = "",
        duration_ms:   float                    = 0.0,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeTransition":
        return cls(
            transition_id = transition_id or str(uuid.uuid4()),
            session_id    = session_id,
            from_state    = from_state,
            to_state      = to_state,
            actor         = actor,
            reason        = reason,
            occurred_at   = time.time(),
            duration_ms   = duration_ms,
            metadata      = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "session_id":    self.session_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "actor":         self.actor,
            "reason":        self.reason,
            "occurred_at":   self.occurred_at,
            "duration_ms":   self.duration_ms,
        }
