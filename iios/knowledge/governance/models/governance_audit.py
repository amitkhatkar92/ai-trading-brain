"""
iios/knowledge/governance/models/governance_audit.py
=====================================================
GovernanceAuditEntry — immutable audit record for every governance
lifecycle event (submission, approval, rejection, certification, etc.).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..governance_constants import (
    GovernanceAction,
    SYSTEM_GOVERNANCE_ACTOR,
)

__all__ = ["GovernanceAuditEntry"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class GovernanceAuditEntry:
    """Single governance lifecycle event record."""

    audit_id:    str             = field(default_factory=_new_id)
    knowledge_id:str             = ""
    action:      GovernanceAction= GovernanceAction.SUBMIT

    actor:       str             = SYSTEM_GOVERNANCE_ACTOR
    reason:      str             = ""

    gov_record_id: Optional[str] = None   # linked GovernanceRecord
    cert_id:     Optional[str]   = None   # linked Certification

    kqi_before:  Optional[float] = None
    kqi_after:   Optional[float] = None

    details:     dict[str, Any]  = field(default_factory=dict)
    created_at:  float           = field(default_factory=time.time)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id":      self.audit_id,
            "knowledge_id":  self.knowledge_id,
            "action":        self.action.value,
            "actor":         self.actor,
            "reason":        self.reason,
            "gov_record_id": self.gov_record_id,
            "cert_id":       self.cert_id,
            "kqi_before":    self.kqi_before,
            "kqi_after":     self.kqi_after,
            "details":       dict(self.details),
            "created_at":    self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GovernanceAuditEntry":
        return cls(
            audit_id      = d.get("audit_id",      _new_id()),
            knowledge_id  = d.get("knowledge_id",  ""),
            action        = GovernanceAction(d.get("action", GovernanceAction.SUBMIT.value)),
            actor         = d.get("actor",         SYSTEM_GOVERNANCE_ACTOR),
            reason        = d.get("reason",        ""),
            gov_record_id = d.get("gov_record_id"),
            cert_id       = d.get("cert_id"),
            kqi_before    = d.get("kqi_before"),
            kqi_after     = d.get("kqi_after"),
            details       = dict(d.get("details",  {})),
            created_at    = d.get("created_at",    time.time()),
        )
