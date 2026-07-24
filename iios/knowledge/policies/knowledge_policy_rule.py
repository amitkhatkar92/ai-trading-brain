"""
knowledge_policy_rule.py — iios.knowledge.policies
----------------------------------------------------
PolicyRule — a named governance rule containing conditions and an action.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constants import PolicyAction, PolicyPriority
from .knowledge_policy_condition import PolicyCondition
from .knowledge_policy_result import PolicyRuleResult


@dataclass(frozen=True)
class PolicyRule:
    """
    A named governance rule.

    A rule is triggered when ALL its conditions evaluate to True (AND logic).
    When triggered, it produces the configured PolicyAction.

    Rules with no conditions are unconditionally triggered.
    """
    rule_id:      str
    name:         str
    description:  str
    conditions:   tuple           # Tuple[PolicyCondition]
    action:       PolicyAction
    priority:     PolicyPriority
    is_mandatory: bool
    metadata:     Dict[str, Any]

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:         str,
        action:       PolicyAction,
        *,
        rule_id:      str                            = "",
        description:  str                            = "",
        conditions:   Optional[List[PolicyCondition]] = None,
        priority:     PolicyPriority                 = PolicyPriority.MEDIUM,
        is_mandatory: bool                           = False,
        metadata:     Optional[Dict[str, Any]]       = None,
    ) -> "PolicyRule":
        return cls(
            rule_id      = rule_id or f"rule-{uuid.uuid4().hex[:10]}",
            name         = name,
            description  = description,
            conditions   = tuple(conditions or []),
            action       = action,
            priority     = priority,
            is_mandatory = is_mandatory,
            metadata     = dict(metadata or {}),
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, artifact: Dict[str, Any]) -> PolicyRuleResult:
        """
        Evaluate all conditions against an artifact (AND logic).

        Returns a PolicyRuleResult.  Never raises.
        """
        if not self.conditions:
            # No conditions → unconditionally triggered
            return PolicyRuleResult(
                rule_id          = self.rule_id,
                rule_name        = self.name,
                passed           = True,
                action           = self.action,
                conditions_met   = 0,
                conditions_total = 0,
                reason           = "No conditions — rule always applies",
            )

        met   = sum(1 for c in self.conditions if c.evaluate(artifact))
        total = len(self.conditions)
        passed = met == total

        return PolicyRuleResult(
            rule_id          = self.rule_id,
            rule_name        = self.name,
            passed           = passed,
            action           = self.action,
            conditions_met   = met,
            conditions_total = total,
            reason           = f"{met}/{total} conditions met",
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":      self.rule_id,
            "name":         self.name,
            "description":  self.description,
            "conditions":   [c.to_dict() for c in self.conditions],
            "action":       self.action.value,
            "priority":     self.priority.name,
            "is_mandatory": self.is_mandatory,
            "metadata":     self.metadata,
        }
