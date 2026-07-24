"""
integration_state.py — iios.integration.lifecycle
--------------------------------------------------
IntegrationStateRecord — immutable record of a session's state at a point in time.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import ACTOR_LIFECYCLE, IntegrationLifecycleState


@dataclass(frozen=True)
class IntegrationStateRecord:
    """
    An immutable snapshot of the lifecycle state of an integration session
    at a specific moment.

    Recorded whenever a session enters a new state.
    Forms part of the immutable audit history.
    """
    record_id:  str
    session_id: str
    state:      IntegrationLifecycleState
    entered_at: str
    actor:      str
    reason:     str

    @classmethod
    def create(
        cls,
        session_id: str,
        state:      IntegrationLifecycleState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> "IntegrationStateRecord":
        return cls(
            record_id  = f"sr-{uuid.uuid4().hex[:12]}",
            session_id = session_id,
            state      = state,
            entered_at = datetime.now(tz=timezone.utc).isoformat(),
            actor      = actor,
            reason     = reason,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":  self.record_id,
            "session_id": self.session_id,
            "state":      self.state.value,
            "entered_at": self.entered_at,
            "actor":      self.actor,
            "reason":     self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IntegrationStateRecord":
        return cls(
            record_id  = d["record_id"],
            session_id = d["session_id"],
            state      = IntegrationLifecycleState(d["state"]),
            entered_at = d["entered_at"],
            actor      = d.get("actor", ACTOR_LIFECYCLE),
            reason     = d.get("reason", ""),
        )
