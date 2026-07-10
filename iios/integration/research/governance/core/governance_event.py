"""core/governance_event.py — Governance domain events."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GovernanceEvent:
    """
    An immutable domain event raised within the Governance Framework.

    Events are appended to GovernanceHistory and can be subscribed to via
    callbacks registered with the engine.
    """
    event_id:    str
    event_type:  str         # e.g. "project.created", "approval.granted"
    entity_type: str         # "project" | "artifact" | "approval" | ...
    entity_id:   str
    actor:       Optional[str]
    payload:     dict[str, Any]
    occurred_at: float

    @classmethod
    def create(
        cls,
        event_type:  str,
        entity_type: str,
        entity_id:   str,
        *,
        event_id:    Optional[str]   = None,
        actor:       Optional[str]   = None,
        payload:     Optional[dict]  = None,
    ) -> "GovernanceEvent":
        return cls(
            event_id    = event_id or f"gve_{uuid.uuid4().hex[:10]}",
            event_type  = event_type,
            entity_type = entity_type,
            entity_id   = entity_id,
            actor       = actor,
            payload     = payload or {},
            occurred_at = time.time(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type,
            "entity_type": self.entity_type,
            "entity_id":   self.entity_id,
            "actor":       self.actor,
            "payload":     self.payload,
            "occurred_at": self.occurred_at,
        }
