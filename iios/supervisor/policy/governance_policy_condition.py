"""
governance_policy_condition.py — iios.supervisor.policy
---------------------------------------------------------
Immutable atomic governance condition — tests one field in the evaluation
inputs against a threshold using a :class:`~.constants.ConditionOperator`.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION, ConditionOperator


@dataclass(frozen=True)
class GovernancePolicyCondition:
    """
    Immutable atomic governance condition.

    Fields
    ------
    condition_id :   Unique identifier.
    name :           Human-readable name.
    field_path :     Dot-separated path into the inputs dict
                     (e.g. ``"health.overall"``, ``"platform.availability"``).
    operator :       Comparison operator.
    threshold :      Value compared against the resolved field value.
                     Ignored for EXISTS/NOT_EXISTS/IS_TRUE/IS_FALSE operators.
    description :    Optional human-readable description.
    metadata :       Supplementary metadata.
    framework_version : Framework version string.
    """
    condition_id:      str
    name:              str
    field_path:        str
    operator:          ConditionOperator
    threshold:         Any            = None
    description:       str            = ""
    metadata:          Dict[str, Any] = field(default_factory=dict)
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        name:       str,
        field_path: str,
        operator:   ConditionOperator,
        *,
        threshold:    Any                      = None,
        condition_id: Optional[str]            = None,
        description:  str                      = "",
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> "GovernancePolicyCondition":
        return cls(
            condition_id = condition_id or str(uuid.uuid4()),
            name         = name,
            field_path   = field_path,
            operator     = operator,
            threshold    = threshold,
            description  = description,
            metadata     = dict(metadata or {}),
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
