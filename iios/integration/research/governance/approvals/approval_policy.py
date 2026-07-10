"""approvals/approval_policy.py — Configurable approval policy definitions."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import PolicyType, ReviewStage


@dataclass
class ApprovalPolicy:
    """
    Defines which review stages are required and in what order,
    plus per-stage timeouts.

    Policies are fully data-driven — no logic is hardcoded here.
    """
    policy_id:      str
    name:           str
    policy_type:    PolicyType
    stages:         list[ReviewStage]          # ordered required stages
    stage_timeouts: dict[str, int]             # stage.value → timeout_days
    requires_all:   bool                       # True = all stages must approve
    created_at:     float
    enabled:        bool
    metadata:       dict[str, Any]

    @classmethod
    def create(
        cls,
        name:        str,
        policy_type: PolicyType,
        stages:      list[ReviewStage],
        *,
        policy_id:      Optional[str]  = None,
        requires_all:   bool           = True,
        stage_timeouts: Optional[dict] = None,
        enabled:        bool           = True,
        metadata:       Optional[dict] = None,
    ) -> "ApprovalPolicy":
        return cls(
            policy_id      = policy_id or f"ap_{uuid.uuid4().hex[:10]}",
            name           = name,
            policy_type    = policy_type,
            stages         = stages,
            stage_timeouts = stage_timeouts or {},
            requires_all   = requires_all,
            created_at     = time.time(),
            enabled        = enabled,
            metadata       = metadata or {},
        )

    def timeout_for_stage(self, stage: ReviewStage, default_days: int = 30) -> int:
        return self.stage_timeouts.get(stage.value, default_days)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id":      self.policy_id,
            "name":           self.name,
            "policy_type":    self.policy_type.value,
            "stages":         [s.value for s in self.stages],
            "stage_timeouts": self.stage_timeouts,
            "requires_all":   self.requires_all,
            "enabled":        self.enabled,
            "created_at":     self.created_at,
        }
