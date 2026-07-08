"""iios/decision_governance/approval/approval_result.py

Dataclasses for individual approval records and aggregate results.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.decision_governance.governance_constants import (
    ApprovalLevel,
    ApprovalMode,
    ApprovalStatus,
)


@dataclass
class ApprovalRecord:
    """One approval decision produced by a single ApprovalPolicy step."""

    record_id:   str          = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str          = ""
    policy_id:   str          = ""
    policy_name: str          = ""
    level:       ApprovalLevel = ApprovalLevel.AUTO
    mode:        ApprovalMode  = ApprovalMode.AUTOMATIC
    status:      ApprovalStatus = ApprovalStatus.APPROVED
    approver:    str          = "system"
    reason:      str          = ""
    timestamp:   float        = field(default_factory=time.time)
    expires_at:  float | None = None
    metadata:    dict         = field(default_factory=dict)

    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "record_id":   self.record_id,
            "decision_id": self.decision_id,
            "policy_id":   self.policy_id,
            "policy_name": self.policy_name,
            "level":       self.level.value,
            "mode":        self.mode.value,
            "status":      self.status.value,
            "approver":    self.approver,
            "reason":      self.reason,
            "timestamp":   self.timestamp,
            "expires_at":  self.expires_at,
            "metadata":    self.metadata,
        }


@dataclass
class ApprovalResult:
    """Aggregate result of the full approval workflow for one decision."""

    result_id:     str           = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id:   str           = ""
    status:        ApprovalStatus = ApprovalStatus.APPROVED
    approved:      bool          = True
    records:       list[ApprovalRecord] = field(default_factory=list)
    escalations:   int           = 0
    current_level: ApprovalLevel = ApprovalLevel.AUTO
    created_at:    float         = field(default_factory=time.time)
    expires_at:    float | None  = None

    def to_dict(self) -> dict:
        return {
            "result_id":     self.result_id,
            "decision_id":   self.decision_id,
            "status":        self.status.value,
            "approved":      self.approved,
            "records":       [r.to_dict() for r in self.records],
            "escalations":   self.escalations,
            "current_level": self.current_level.value,
            "created_at":    self.created_at,
            "expires_at":    self.expires_at,
        }
