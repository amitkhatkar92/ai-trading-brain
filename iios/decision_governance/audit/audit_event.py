"""iios/decision_governance/audit/audit_event.py

AuditEvent dataclass — the atomic unit of the audit trail.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.decision_governance.governance_constants import AuditEventType


@dataclass
class AuditEvent:
    """
    Immutable record of a single governance action.

    ``evidence`` carries reasoning / policy / optimization traces.
    """

    event_id:    str           = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str           = ""
    event_type:  AuditEventType = AuditEventType.SUBMITTED
    actor:       str           = "system"
    action:      str           = ""
    details:     dict          = field(default_factory=dict)
    evidence:    dict          = field(default_factory=dict)
    timestamp:   float         = field(default_factory=time.time)
    session_id:  str           = ""

    def to_dict(self) -> dict:
        return {
            "event_id":    self.event_id,
            "decision_id": self.decision_id,
            "event_type":  self.event_type.value,
            "actor":       self.actor,
            "action":      self.action,
            "details":     self.details,
            "evidence":    self.evidence,
            "timestamp":   self.timestamp,
            "session_id":  self.session_id,
        }
