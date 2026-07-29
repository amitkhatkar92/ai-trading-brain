"""
audit_record.py -- iios.ai.governance.audit
============================================
:class:`AuditEventType` — classification of auditable events.
:class:`AuditRecord`    — immutable, tamper-evident audit record.
:class:`AuditEvent`     — lightweight audit event emitted before full record creation.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class AuditEventType(str, Enum):
    """Classification of auditable events."""
    POLICY_EVALUATED  = "policy_evaluated"
    PERMISSION_CHECK  = "permission_check"
    DECISION_ISSUED   = "decision_issued"
    RISK_ASSESSED     = "risk_assessed"
    COMPLIANCE_CHECKED = "compliance_checked"
    AGENT_ACTION      = "agent_action"
    MODEL_INVOCATION  = "model_invocation"
    DATA_ACCESS       = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    ESCALATION        = "escalation"


@dataclass(frozen=True)
class AuditRecord:
    """
    Immutable, tamper-evident audit record.

    ``record_hash`` — SHA-256 of the core fields for tamper detection.
    ``previous_hash`` — hash of the preceding record to form a chain.
    """

    record_id:     str
    event_type:    AuditEventType
    subject_id:    str
    principal_id:  str
    action:        str
    resource:      str
    outcome:       str            # "allowed" / "denied" / "escalated" / "error"
    context:       FrozenSet[Tuple[str, Any]]
    occurred_at:   float
    record_hash:   str
    previous_hash: str
    notes:         str

    @classmethod
    def create(
        cls,
        event_type:    AuditEventType,
        subject_id:    str,
        principal_id:  str,
        action:        str,
        resource:      str,
        outcome:       str,
        previous_hash: str = "",
        notes:         str = "",
        **context: Any,
    ) -> "AuditRecord":
        record_id   = str(uuid.uuid4())
        occurred_at = time.time()
        ctx         = frozenset(context.items())
        raw         = json.dumps({
            "record_id":    record_id,
            "event_type":   event_type.value,
            "subject_id":   subject_id,
            "principal_id": principal_id,
            "action":       action,
            "resource":     resource,
            "outcome":      outcome,
            "occurred_at":  occurred_at,
            "previous_hash": previous_hash,
        }, sort_keys=True)
        record_hash = hashlib.sha256(raw.encode()).hexdigest()
        return cls(
            record_id     = record_id,
            event_type    = event_type,
            subject_id    = subject_id,
            principal_id  = principal_id,
            action        = action,
            resource      = resource,
            outcome       = outcome,
            context       = ctx,
            occurred_at   = occurred_at,
            record_hash   = record_hash,
            previous_hash = previous_hash,
            notes         = notes,
        )

    def verify_integrity(self) -> bool:
        """Recompute the hash and confirm it matches ``record_hash``."""
        raw = json.dumps({
            "record_id":    self.record_id,
            "event_type":   self.event_type.value,
            "subject_id":   self.subject_id,
            "principal_id": self.principal_id,
            "action":       self.action,
            "resource":     self.resource,
            "outcome":      self.outcome,
            "occurred_at":  self.occurred_at,
            "previous_hash": self.previous_hash,
        }, sort_keys=True)
        expected = hashlib.sha256(raw.encode()).hexdigest()
        return self.record_hash == expected


@dataclass(frozen=True)
class AuditEvent:
    """Lightweight event emitted to the event bus when an audit record is created."""

    event_id:  str
    audit_id:  str
    event_type: AuditEventType
    subject_id: str
    action:    str
    occurred_at: float

    @classmethod
    def from_record(cls, record: AuditRecord) -> "AuditEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            audit_id    = record.record_id,
            event_type  = record.event_type,
            subject_id  = record.subject_id,
            action      = record.action,
            occurred_at = record.occurred_at,
        )
