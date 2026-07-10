"""iios/execution/monitoring/audit/audit_event.py"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    AUDIT_HASH_ALGORITHM,
    AuditEventType,
)


def _compute_hash(data: dict[str, Any]) -> str:
    """Deterministic SHA-256 hash of a JSON-serialisable dict."""
    serialised = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()


@dataclass
class AuditEvent:
    """
    Immutable audit record.  Content hash prevents tampering.

    Once created, fields must not be modified (enforced by convention —
    dataclasses do not have frozen=True here to allow
    __post_init__ to compute the hash).
    """

    event_type:    AuditEventType
    entity_type:   str              = ""
    entity_id:     str              = ""
    broker_id:     str              = ""
    action:        str              = ""
    before_state:  dict[str, Any]   = field(default_factory=dict)
    after_state:   dict[str, Any]   = field(default_factory=dict)
    user_id:       str              = "system"
    source:        str              = ""
    event_id:      str              = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:     float            = field(default_factory=time.time)
    metadata:      dict[str, Any]   = field(default_factory=dict)
    content_hash:  str              = ""   # computed in __post_init__

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = _compute_hash(self._hashable_payload())

    def _hashable_payload(self) -> dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "entity_type": self.entity_type,
            "entity_id":   self.entity_id,
            "action":      self.action,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "user_id":     self.user_id,
            "timestamp":   self.timestamp,
        }

    def verify_integrity(self) -> bool:
        """Return True if the stored hash matches the computed hash."""
        return self.content_hash == _compute_hash(self._hashable_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "entity_type":  self.entity_type,
            "entity_id":    self.entity_id,
            "broker_id":    self.broker_id,
            "action":       self.action,
            "before_state": self.before_state,
            "after_state":  self.after_state,
            "user_id":      self.user_id,
            "source":       self.source,
            "timestamp":    self.timestamp,
            "content_hash": self.content_hash,
            "metadata":     self.metadata,
        }
