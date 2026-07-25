"""
workflow_policy_condition.py — iios.workflow.policies
-------------------------------------------------------
PolicyCondition — a single evaluable condition for a policy rule.

Conditions evaluate fields from the WorkflowPolicyContext using
a configurable operator and value.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import ConditionOperator


@dataclass(frozen=True)
class PolicyCondition:
    """
    An evaluable condition for a policy rule.

    The `field` is a dot-notation path into the context's flat dict
    representation (e.g. "security_context.user_role",
    "resource_context.estimated_cost", "workflow_type").

    The `operator` defines the comparison to perform.
    The `value` is the expected value to compare against.
    """
    condition_id: str
    field:        str
    operator:     ConditionOperator
    value:        Any
    description:  str

    @classmethod
    def create(
        cls,
        field:       str,
        operator:    ConditionOperator,
        value:       Any               = None,
        *,
        description: str               = "",
        condition_id: Optional[str]    = None,
    ) -> "PolicyCondition":
        return cls(
            condition_id = condition_id or f"pcond-{uuid.uuid4().hex[:10]}",
            field        = field,
            operator     = operator,
            value        = value,
            description  = description,
        )

    def evaluate(self, context_data: Dict[str, Any]) -> bool:
        """
        Evaluate this condition against a flat context dictionary.

        Returns True if the condition is satisfied.
        """
        field_val = self._get_field(context_data, self.field)
        return self._apply_operator(field_val)

    def _get_field(self, data: Dict[str, Any], path: str) -> Any:
        """Resolve a dot-notation path through nested dicts."""
        parts = path.split(".")
        current: Any = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _apply_operator(self, field_val: Any) -> bool:
        op = self.operator
        v  = self.value

        if op == ConditionOperator.IS_NULL:
            return field_val is None

        if op == ConditionOperator.IS_NOT_NULL:
            return field_val is not None

        if field_val is None:
            return False

        if op == ConditionOperator.EQUALS:
            return field_val == v

        if op == ConditionOperator.NOT_EQUALS:
            return field_val != v

        if op == ConditionOperator.GREATER_THAN:
            try:
                return float(field_val) > float(v)
            except (TypeError, ValueError):
                return False

        if op == ConditionOperator.LESS_THAN:
            try:
                return float(field_val) < float(v)
            except (TypeError, ValueError):
                return False

        if op == ConditionOperator.GREATER_THAN_OR_EQUAL:
            try:
                return float(field_val) >= float(v)
            except (TypeError, ValueError):
                return False

        if op == ConditionOperator.LESS_THAN_OR_EQUAL:
            try:
                return float(field_val) <= float(v)
            except (TypeError, ValueError):
                return False

        if op == ConditionOperator.IN:
            try:
                return field_val in v
            except TypeError:
                return False

        if op == ConditionOperator.NOT_IN:
            try:
                return field_val not in v
            except TypeError:
                return False

        if op == ConditionOperator.CONTAINS:
            try:
                return v in field_val
            except TypeError:
                return False

        if op == ConditionOperator.NOT_CONTAINS:
            try:
                return v not in field_val
            except TypeError:
                return False

        if op == ConditionOperator.STARTS_WITH:
            return str(field_val).startswith(str(v))

        if op == ConditionOperator.ENDS_WITH:
            return str(field_val).endswith(str(v))

        if op == ConditionOperator.MATCHES:
            try:
                return bool(re.match(str(v), str(field_val)))
            except re.error:
                return False

        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "field":        self.field,
            "operator":     self.operator.value,
            "value":        self.value,
            "description":  self.description,
        }
