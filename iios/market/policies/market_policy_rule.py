"""
market_policy_rule.py — iios.market.policies
==============================================
Immutable market policy rule value object.

A rule combines one or more :class:`~.market_policy_condition.MarketPolicyCondition`
objects with a :class:`~.constants.LogicalOperator` and maps to a
:class:`~.constants.PolicyAction` when the conditions are satisfied.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION, LogicalOperator, PolicyAction
from .market_policy_condition import MarketPolicyCondition


@dataclass(frozen=True)
class MarketPolicyRule:
    """
    Immutable market policy rule.

    A rule is the mapping: ``conditions [logical_op] => action``.

    When the logical operator is :attr:`LogicalOperator.ALL`, all conditions
    must be satisfied.  When :attr:`LogicalOperator.ANY`, at least one must
    be satisfied.

    Fields
    ------
    rule_id :           Unique identifier.
    name :              Human-readable name.
    conditions :        Ordered tuple of conditions.
    logical_operator :  How conditions are combined.
    action :            Governance outcome when conditions are satisfied.
    weight :            Numeric weight for WEIGHTED evaluation mode (default 1.0).
    description :       Optional human-readable description.
    metadata :          Supplementary metadata.
    framework_version : Framework version string.
    """
    rule_id:           str
    name:              str
    conditions:        Tuple[MarketPolicyCondition, ...]
    logical_operator:  LogicalOperator
    action:            PolicyAction
    weight:            float           = 1.0
    description:       str             = ""
    metadata:          Dict[str, Any]  = field(default_factory=dict)
    framework_version: str             = VERSION

    @classmethod
    def create(
        cls,
        name:             str,
        conditions:       Tuple[MarketPolicyCondition, ...],
        logical_operator: LogicalOperator,
        action:           PolicyAction,
        *,
        rule_id:     Optional[str]            = None,
        weight:      float                    = 1.0,
        description: str                      = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "MarketPolicyRule":
        return cls(
            rule_id          = rule_id or str(uuid.uuid4()),
            name             = name,
            conditions       = tuple(conditions),
            logical_operator = logical_operator,
            action           = action,
            weight           = weight,
            description      = description,
            metadata         = dict(metadata or {}),
        )

    @property
    def condition_count(self) -> int:
        return len(self.conditions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":           self.rule_id,
            "name":              self.name,
            "conditions":        [c.to_dict() for c in self.conditions],
            "logical_operator":  self.logical_operator.value,
            "action":            self.action.value,
            "weight":            self.weight,
            "description":       self.description,
            "framework_version": self.framework_version,
        }
