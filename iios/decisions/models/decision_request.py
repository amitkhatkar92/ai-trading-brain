"""
iios/decisions/models/decision_request.py
==========================================
DecisionRequest — the input contract for the Decision Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..decision_constants import (
    DecisionPriority,
    DecisionType,
    DEFAULT_DECISION_TTL_S,
)
from .decision_option import DecisionOption


@dataclass
class DecisionRequest:
    """
    Input object submitted to the Decision Engine.

    Attributes
    ----------
    request_id          : Unique request identifier.
    decision_type       : Preferred decision type, or None for inferred.
    source_id           : Originating engine / module.
    options             : Pre-supplied candidate options (can be empty;
                          the workflow GENERATES options when empty).
    intelligence_payload: Raw intelligence products (list of dicts).
    context             : Free-form decision context.
    constraints         : Caller-supplied constraints.
    priority            : Request urgency.
    ttl_s               : Time-to-live in seconds.
    metadata            : Caller-supplied extras.
    created_at          : Unix timestamp.
    """

    request_id:           str                    = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type:        DecisionType | None     = None
    source_id:            str                    = ""
    options:              list[DecisionOption]   = field(default_factory=list)
    intelligence_payload: list[dict[str, Any]]   = field(default_factory=list)
    context:              dict[str, Any]          = field(default_factory=dict)
    constraints:          dict[str, Any]          = field(default_factory=dict)
    priority:             DecisionPriority        = DecisionPriority.MEDIUM
    ttl_s:                float                  = DEFAULT_DECISION_TTL_S
    metadata:             dict[str, Any]          = field(default_factory=dict)
    created_at:           float                  = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":           self.request_id,
            "decision_type":        self.decision_type.value if self.decision_type else None,
            "source_id":            self.source_id,
            "options":              [o.to_dict() for o in self.options],
            "intelligence_payload": list(self.intelligence_payload),
            "context":              dict(self.context),
            "constraints":          dict(self.constraints),
            "priority":             self.priority.value,
            "ttl_s":                self.ttl_s,
            "metadata":             dict(self.metadata),
            "created_at":           self.created_at,
        }
