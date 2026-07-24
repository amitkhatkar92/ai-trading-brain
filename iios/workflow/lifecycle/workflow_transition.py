"""
workflow_transition.py — iios.workflow.lifecycle
--------------------------------------------------
WorkflowTransition — immutable record of a lifecycle state machine transition.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import ACTOR_LIFECYCLE, WorkflowLifecycleState


@dataclass(frozen=True)
class WorkflowTransition:
    """
    An immutable audit record of a workflow lifecycle state transition.

    Every permitted state change produces one WorkflowTransition.
    The transition history is append-only and never modified.
    """
    transition_id:   str
    session_id:      str
    from_state:      WorkflowLifecycleState
    to_state:        WorkflowLifecycleState
    actor:           str
    reason:          str
    transitioned_at: str

    @classmethod
    def create(
        cls,
        session_id: str,
        from_state: WorkflowLifecycleState,
        to_state:   WorkflowLifecycleState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> "WorkflowTransition":
        return cls(
            transition_id   = f"wtr-{uuid.uuid4().hex[:12]}",
            session_id      = session_id,
            from_state      = from_state,
            to_state        = to_state,
            actor           = actor,
            reason          = reason,
            transitioned_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id":   self.transition_id,
            "session_id":      self.session_id,
            "from_state":      self.from_state.value,
            "to_state":        self.to_state.value,
            "actor":           self.actor,
            "reason":          self.reason,
            "transitioned_at": self.transitioned_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowTransition":
        return cls(
            transition_id   = d["transition_id"],
            session_id      = d["session_id"],
            from_state      = WorkflowLifecycleState(d["from_state"]),
            to_state        = WorkflowLifecycleState(d["to_state"]),
            actor           = d.get("actor", ACTOR_LIFECYCLE),
            reason          = d.get("reason", ""),
            transitioned_at = d["transitioned_at"],
        )
