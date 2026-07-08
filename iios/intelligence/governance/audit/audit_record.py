"""
iios/intelligence/governance/audit/audit_record.py
===================================================
AuditRecord — the immutable audit log entry model.
Lives in its own module to avoid circular imports.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..quality_constants import AuditEventType, IntelligenceType


@dataclass
class AuditRecord:
    """
    Immutable audit log entry created for every governance event.

    Attributes
    ----------
    audit_id     : Unique entry identifier.
    event_type   : Type of governance event.
    record_id    : Associated QualityRecord.
    product_id   : Intelligence product being governed.
    product_type : Product category.
    source_id    : Originating engine/module.
    actor_id     : Entity that caused the event.
    payload      : Event-specific context.
    metadata     : Caller-supplied extras.
    created_at   : Unix timestamp (immutable).
    """

    audit_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:   AuditEventType   = AuditEventType.EVALUATION
    record_id:    str              = ""
    product_id:   str              = ""
    product_type: IntelligenceType = IntelligenceType.GENERIC
    source_id:    str              = ""
    actor_id:     str              = ""
    payload:      dict[str, Any]   = field(default_factory=dict)
    metadata:     dict[str, Any]   = field(default_factory=dict)
    created_at:   float            = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id":     self.audit_id,
            "event_type":   self.event_type.value,
            "record_id":    self.record_id,
            "product_id":   self.product_id,
            "product_type": self.product_type.value,
            "source_id":    self.source_id,
            "actor_id":     self.actor_id,
            "payload":      self.payload,
            "metadata":     self.metadata,
            "created_at":   self.created_at,
        }
