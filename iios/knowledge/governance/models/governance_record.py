"""
iios/knowledge/governance/models/governance_record.py
======================================================
GovernanceRecord — one approval/rejection record for a knowledge item.

Each submission creates a new GovernanceRecord.  Multiple records may
exist for the same knowledge item (successive submissions after edits).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..governance_constants import (
    ApprovalStatus,
    SYSTEM_GOVERNANCE_ACTOR,
    GOVERNANCE_SCHEMA_VERSION,
)

__all__ = ["GovernanceRecord"]


_GOVERNANCE_SCHEMA_VERSION = GOVERNANCE_SCHEMA_VERSION


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class GovernanceRecord:
    """Approval / rejection record for one knowledge submission."""

    gov_id:              str            = field(default_factory=_new_id)
    knowledge_id:        str            = ""

    status:              ApprovalStatus = ApprovalStatus.PENDING
    submitted_by:        str            = SYSTEM_GOVERNANCE_ACTOR
    submitted_at:        float          = field(default_factory=time.time)

    # Review details (populated on approve/reject)
    reviewed_by:         Optional[str]  = None
    reviewed_at:         Optional[float]= None
    decision_reason:     str            = ""

    # Quality info at submission time
    kqi_at_submission:   float          = 0.0
    violations_count:    int            = 0

    # Which policies were evaluated
    policy_ids_applied:  list[str]      = field(default_factory=list)

    # Extended notes
    notes:               str            = ""
    attributes:          dict[str, Any] = field(default_factory=dict)

    schema_version:      str            = _GOVERNANCE_SCHEMA_VERSION

    # ── Lifecycle helpers ─────────────────────────────────────────────────────

    @property
    def is_pending(self) -> bool:
        return self.status in (ApprovalStatus.PENDING, ApprovalStatus.UNDER_REVIEW,
                                ApprovalStatus.ESCALATED)

    @property
    def is_approved(self) -> bool:
        return self.status in (ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED)

    @property
    def is_rejected(self) -> bool:
        return self.status == ApprovalStatus.REJECTED

    @property
    def is_revoked(self) -> bool:
        return self.status == ApprovalStatus.REVOKED

    def approve(self, reviewed_by: str, reason: str = "") -> None:
        self.status          = ApprovalStatus.APPROVED
        self.reviewed_by     = reviewed_by
        self.reviewed_at     = time.time()
        self.decision_reason = reason

    def auto_approve(self, reason: str = "") -> None:
        self.status          = ApprovalStatus.AUTO_APPROVED
        self.reviewed_by     = SYSTEM_GOVERNANCE_ACTOR
        self.reviewed_at     = time.time()
        self.decision_reason = reason or "Auto-approved by policy"

    def reject(self, reviewed_by: str, reason: str = "") -> None:
        self.status          = ApprovalStatus.REJECTED
        self.reviewed_by     = reviewed_by
        self.reviewed_at     = time.time()
        self.decision_reason = reason

    def revoke(self, revoked_by: str, reason: str = "") -> None:
        self.status          = ApprovalStatus.REVOKED
        self.reviewed_by     = revoked_by
        self.reviewed_at     = time.time()
        self.decision_reason = reason

    def set_under_review(self, reviewer: str) -> None:
        self.status      = ApprovalStatus.UNDER_REVIEW
        self.reviewed_by = reviewer

    def escalate(self, reason: str = "") -> None:
        self.status          = ApprovalStatus.ESCALATED
        self.decision_reason = reason

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "gov_id":             self.gov_id,
            "knowledge_id":       self.knowledge_id,
            "status":             self.status.value,
            "submitted_by":       self.submitted_by,
            "submitted_at":       self.submitted_at,
            "reviewed_by":        self.reviewed_by,
            "reviewed_at":        self.reviewed_at,
            "decision_reason":    self.decision_reason,
            "kqi_at_submission":  self.kqi_at_submission,
            "violations_count":   self.violations_count,
            "policy_ids_applied": list(self.policy_ids_applied),
            "notes":              self.notes,
            "attributes":         dict(self.attributes),
            "schema_version":     self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GovernanceRecord":
        return cls(
            gov_id             = d.get("gov_id",             _new_id()),
            knowledge_id       = d.get("knowledge_id",       ""),
            status             = ApprovalStatus(d.get("status", ApprovalStatus.PENDING.value)),
            submitted_by       = d.get("submitted_by",       SYSTEM_GOVERNANCE_ACTOR),
            submitted_at       = d.get("submitted_at",       time.time()),
            reviewed_by        = d.get("reviewed_by"),
            reviewed_at        = d.get("reviewed_at"),
            decision_reason    = d.get("decision_reason",    ""),
            kqi_at_submission  = d.get("kqi_at_submission",  0.0),
            violations_count   = d.get("violations_count",   0),
            policy_ids_applied = list(d.get("policy_ids_applied", [])),
            notes              = d.get("notes",              ""),
            attributes         = dict(d.get("attributes",     {})),
            schema_version     = d.get("schema_version",     _GOVERNANCE_SCHEMA_VERSION),
        )
