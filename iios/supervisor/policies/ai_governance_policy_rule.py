"""
ai_governance_policy_rule.py — iios.supervisor.policies
---------------------------------------------------------
Immutable governance policy rule value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION, AIGovernancePolicyAction, LogicalOperator
from .ai_governance_policy_condition import AIGovernancePolicyCondition


@dataclass(frozen=True)
class AIGovernancePolicyRule:
    """
    Immutable governance policy rule.

    A rule aggregates one or more :class:`AIGovernancePolicyCondition` objects
    via a :class:`LogicalOperator` (ALL / ANY) and prescribes a
    :class:`AIGovernancePolicyAction` when its conditions are satisfied.

    Fields
    ------
    rule_id :           Unique identifier.
    name :              Human-readable label.
    conditions :        Ordered tuple of conditions.
    logical_operator :  How conditions are combined (ALL = AND, ANY = OR).
    action :            Action to prescribe when this rule matches.
    weight :            Relative weight used in WEIGHTED evaluation mode.
    description :       Optional explanation.
    metadata :          Arbitrary extension metadata.
    framework_version : Framework version string.
    """
    rule_id:          str
    name:             str
    conditions:       Tuple[AIGovernancePolicyCondition, ...]
    logical_operator: LogicalOperator
    action:           AIGovernancePolicyAction
    weight:           float            = 1.0
    description:      str              = ""
    metadata:         Dict[str, Any]   = field(default_factory=dict)
    framework_version: str             = VERSION

    @classmethod
    def create(
        cls,
        name:             str,
        conditions:       List[AIGovernancePolicyCondition],
        logical_operator: LogicalOperator,
        action:           AIGovernancePolicyAction,
        *,
        rule_id:     Optional[str]             = None,
        weight:      float                     = 1.0,
        description: str                       = "",
        metadata:    Optional[Dict[str, Any]]  = None,
    ) -> "AIGovernancePolicyRule":
        return cls(
            rule_id          = rule_id or str(uuid.uuid4()),
            name             = name,
            conditions       = tuple(conditions),
            logical_operator = logical_operator,
            action           = action,
            weight           = weight,
            description      = description,
            metadata         = metadata or {},
        )

    @property
    def condition_count(self) -> int:
        """Number of conditions in this rule."""
        return len(self.conditions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":          self.rule_id,
            "name":             self.name,
            "logical_operator": self.logical_operator.value,
            "action":           self.action.value,
            "weight":           self.weight,
            "condition_count":  self.condition_count,
            "description":      self.description,
            "framework_version": self.framework_version,
        }
