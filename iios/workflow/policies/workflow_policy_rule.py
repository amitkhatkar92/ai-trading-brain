"""
workflow_policy_rule.py — iios.workflow.policies
-------------------------------------------------
PolicyRule — a set of conditions that, when all met, triggers a
PolicyAction in the governance framework.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import PolicyAction, PolicyPriorityLevel
from .workflow_policy_condition import PolicyCondition


@dataclass(frozen=True)
class PolicyRule:
    """
    A named set of conditions that triggers a PolicyAction.

    All conditions must be satisfied (AND logic) for the rule to fire.
    If there are no conditions, the rule always fires.

    Rules within a policy are evaluated in priority order.
    The first matching rule determines the policy's result.
    """
    rule_id:     str
    name:        str
    description: str
    conditions:  tuple                  # Tuple[PolicyCondition, ...]
    action:      PolicyAction
    priority:    PolicyPriorityLevel
    enabled:     bool

    @classmethod
    def create(
        cls,
        name:        str,
        action:      PolicyAction,
        *,
        conditions:  Optional[List[PolicyCondition]] = None,
        priority:    PolicyPriorityLevel             = PolicyPriorityLevel.MEDIUM,
        description: str                             = "",
        enabled:     bool                            = True,
        rule_id:     Optional[str]                   = None,
    ) -> "PolicyRule":
        return cls(
            rule_id     = rule_id or f"prule-{uuid.uuid4().hex[:10]}",
            name        = name,
            description = description,
            conditions  = tuple(conditions or []),
            action      = action,
            priority    = priority,
            enabled     = enabled,
        )

    def applies(self, context_data: Dict[str, Any]) -> bool:
        """
        Return True if all conditions are satisfied (rule fires).

        A rule with no conditions always fires.
        Disabled rules never fire.
        """
        if not self.enabled:
            return False
        return all(c.evaluate(context_data) for c in self.conditions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":     self.rule_id,
            "name":        self.name,
            "description": self.description,
            "action":      self.action.value,
            "priority":    self.priority.name,
            "enabled":     self.enabled,
            "conditions":  [c.to_dict() for c in self.conditions],
        }
