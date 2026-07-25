"""
workflow_policy_priority.py — iios.workflow.policies
-----------------------------------------------------
Priority-aware ordering of governance policies for the evaluation chain.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import PolicyPriorityLevel
from .workflow_policy import WorkflowPolicy


@dataclass(order=True)
class PolicyPriorityItem:
    """
    Priority-ordered wrapper for a WorkflowPolicy.

    Implements comparison by (priority, sequence) so that a min-heap
    or sort returns CRITICAL (0) policies before INFORMATIONAL (4).
    Ties are broken by insertion sequence (FIFO).
    """
    priority:  int
    sequence:  int
    item_id:   str         = field(compare=False)
    policy:    WorkflowPolicy = field(compare=False)
    added_at:  str         = field(compare=False)

    @classmethod
    def create(
        cls,
        policy:   WorkflowPolicy,
        sequence: int,
    ) -> "PolicyPriorityItem":
        return cls(
            priority = policy.priority.value,
            sequence = sequence,
            item_id  = f"ppi-{uuid.uuid4().hex[:8]}",
            policy   = policy,
            added_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    @property
    def priority_label(self) -> str:
        return PolicyPriorityLevel(self.priority).name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id":        self.item_id,
            "policy_id":      self.policy.policy_id,
            "policy_name":    self.policy.name,
            "priority":       self.priority,
            "priority_label": self.priority_label,
            "sequence":       self.sequence,
            "added_at":       self.added_at,
        }
