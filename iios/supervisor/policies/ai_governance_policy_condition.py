"""
ai_governance_policy_condition.py — iios.supervisor.policies
--------------------------------------------------------------
Immutable condition value object for AI governance policy rules.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION, ConditionOperator


@dataclass(frozen=True)
class AIGovernancePolicyCondition:
    """
    Immutable condition that evaluates a single field from the governance
    context inputs against a threshold using a comparison operator.

    Fields
    ------
    condition_id :      Unique identifier.
    name :              Human-readable label.
    field_path :        Dot-separated path into the inputs dict.
    operator :          Comparison operator.
    threshold :         Value to compare against (None for EXISTS / IS_TRUE).
    description :       Optional human-readable explanation.
    metadata :          Arbitrary extension metadata.
    framework_version : Framework version string.
    """
    condition_id:      str
    name:              str
    field_path:        str
    operator:          ConditionOperator
    threshold:         Any
    description:       str            = ""
    metadata:          Dict[str, Any] = field(default_factory=dict)
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        name:       str,
        field_path: str,
        operator:   ConditionOperator,
        threshold:  Any = None,
        *,
        condition_id: Optional[str]             = None,
        description:  str                       = "",
        metadata:     Optional[Dict[str, Any]]  = None,
    ) -> "AIGovernancePolicyCondition":
        return cls(
            condition_id = condition_id or str(uuid.uuid4()),
            name         = name,
            field_path   = field_path,
            operator     = operator,
            threshold    = threshold,
            description  = description,
            metadata     = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id":      self.condition_id,
            "name":              self.name,
            "field_path":        self.field_path,
            "operator":          self.operator.value,
            "threshold":         self.threshold,
            "description":       self.description,
            "framework_version": self.framework_version,
        }
