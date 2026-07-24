"""
knowledge_state.py — iios.knowledge.lifecycle
-----------------------------------------------
Immutable state record captured at each lifecycle transition.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import KnowledgeLifecycleState, VERSION


@dataclass(frozen=True)
class KnowledgeStateRecord:
    """
    Immutable snapshot of a knowledge session's state at a given moment.

    Appended to the session's state history on every transition.

    Fields
    ------
    record_id :    Unique record identifier.
    session_id :   Owning knowledge session.
    state :        Lifecycle state at the time of recording.
    actor :        Identity that triggered this state entry.
    reason :       Optional human-readable context (e.g. failure reason).
    recorded_at :  Wall-clock time this record was created.
    metadata :     Supplementary key-value metadata.
    """
    record_id:   str
    session_id:  str
    state:       KnowledgeLifecycleState
    actor:       str
    reason:      str           = ""
    recorded_at: float         = field(default_factory=time.time)
    metadata:    Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: str,
        state:      KnowledgeLifecycleState,
        actor:      str,
        *,
        record_id:  Optional[str]            = None,
        reason:     str                      = "",
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeStateRecord":
        return cls(
            record_id   = record_id or str(uuid.uuid4()),
            session_id  = session_id,
            state       = state,
            actor       = actor,
            reason      = reason,
            metadata    = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":   self.record_id,
            "session_id":  self.session_id,
            "state":       self.state.value,
            "actor":       self.actor,
            "reason":      self.reason,
            "recorded_at": self.recorded_at,
        }
