"""
iios/knowledge/governance/models/policy.py
==========================================
GovernancePolicy — a declarative rule that controls how knowledge records
are admitted, approved, or blocked by the governance engine.

PolicyCondition — a single predicate (field op value) evaluated against
a quality context dict.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..governance_constants import (
    GovernanceAction,
    PolicyType,
    RiskLevel,
    SYSTEM_GOVERNANCE_ACTOR,
    GOVERNANCE_SCHEMA_VERSION,
)

__all__ = ["PolicyCondition", "GovernancePolicy"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class PolicyCondition:
    """Single predicate evaluated against a quality context dict.

    Supported operators: ``>=``, ``<=``, ``>``, ``<``, ``==``, ``!=``,
    ``in``, ``not_in``.
    """

    field:    str   # key in context dict, e.g. "kqi", "domain", "knowledge_type"
    operator: str   # ">=", "<=", ">", "<", "==", "!=", "in", "not_in"
    value:    Any   # comparison value

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Return True if the condition matches *context*."""
        val = context.get(self.field)
        if val is None:
            return False
        op = self.operator
        try:
            if op == ">=":     return val >= self.value
            if op == "<=":     return val <= self.value
            if op == ">":      return val >  self.value
            if op == "<":      return val <  self.value
            if op == "==":     return val == self.value
            if op == "!=":     return val != self.value
            if op == "in":     return val in self.value
            if op == "not_in": return val not in self.value
        except (TypeError, ValueError):
            return False
        return False

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "operator": self.operator, "value": self.value}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PolicyCondition":
        return cls(field=d["field"], operator=d["operator"], value=d["value"])


@dataclass
class GovernancePolicy:
    """Declarative governance policy.

    A policy is active when ``is_active=True``.  Conditions are evaluated
    in order; all must match for the policy to trigger (AND logic).
    Use multiple policies for OR scenarios.
    """

    policy_id:     str              = field(default_factory=_new_id)
    name:          str              = ""
    description:   str              = ""
    policy_type:   PolicyType       = PolicyType.THRESHOLD_GATE
    action:        GovernanceAction = GovernanceAction.APPROVE
    conditions:    list[PolicyCondition] = field(default_factory=list)
    priority:      int              = 50    # 0 (lowest) → 100 (highest); evaluated highest first
    is_active:     bool             = True
    risk_level:    RiskLevel        = RiskLevel.MEDIUM
    created_by:    str              = SYSTEM_GOVERNANCE_ACTOR
    created_at:    float            = field(default_factory=time.time)
    notes:         str              = ""
    schema_version:str              = GOVERNANCE_SCHEMA_VERSION

    def matches(self, context: dict[str, Any]) -> bool:
        """Return True if ALL conditions evaluate to True against *context*."""
        if not self.is_active:
            return False
        return all(c.evaluate(context) for c in self.conditions)

    def add_condition(self, field: str, operator: str, value: Any) -> None:
        self.conditions.append(PolicyCondition(field=field, operator=operator, value=value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id":     self.policy_id,
            "name":          self.name,
            "description":   self.description,
            "policy_type":   self.policy_type.value,
            "action":        self.action.value,
            "conditions":    [c.to_dict() for c in self.conditions],
            "priority":      self.priority,
            "is_active":     self.is_active,
            "risk_level":    self.risk_level.value,
            "created_by":    self.created_by,
            "created_at":    self.created_at,
            "notes":         self.notes,
            "schema_version":self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GovernancePolicy":
        return cls(
            policy_id      = d.get("policy_id",     _new_id()),
            name           = d.get("name",          ""),
            description    = d.get("description",   ""),
            policy_type    = PolicyType(d.get("policy_type", PolicyType.THRESHOLD_GATE.value)),
            action         = GovernanceAction(d.get("action", GovernanceAction.APPROVE.value)),
            conditions     = [PolicyCondition.from_dict(c) for c in d.get("conditions", [])],
            priority       = d.get("priority",      50),
            is_active      = d.get("is_active",     True),
            risk_level     = RiskLevel(d.get("risk_level", RiskLevel.MEDIUM.value)),
            created_by     = d.get("created_by",    SYSTEM_GOVERNANCE_ACTOR),
            created_at     = d.get("created_at",    time.time()),
            notes          = d.get("notes",         ""),
            schema_version = d.get("schema_version",GOVERNANCE_SCHEMA_VERSION),
        )
