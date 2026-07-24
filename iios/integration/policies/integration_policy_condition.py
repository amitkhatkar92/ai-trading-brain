"""
integration_policy_condition.py — iios.integration.policies
-------------------------------------------------------------
IntegrationPolicyCondition — atomic governance condition.

A condition tests a single attribute from the evaluation context
using a comparison operator.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import ConditionOperator


@dataclass(frozen=True)
class IntegrationPolicyCondition:
    """
    An atomic condition within a policy rule.

    Evaluates a context attribute against an expected value using
    the specified operator.  All condition objects are immutable.

    The field_path uses dot-notation to resolve nested attributes in
    the evaluation context dict, e.g. ``security_config.tls_required``.
    """

    condition_id:   str
    name:           str
    field_path:     str              # dot-path into evaluation context
    operator:       ConditionOperator
    expected_value: Any              # expected value or list
    description:    str
    metadata:       Dict[str, Any]
    created_at:     str

    # ── factory ───────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:           str,
        field_path:     str,
        operator:       ConditionOperator,
        expected_value: Any                       = None,
        *,
        description:    str                       = "",
        metadata:       Optional[Dict[str, Any]]  = None,
        condition_id:   Optional[str]             = None,
    ) -> "IntegrationPolicyCondition":
        return cls(
            condition_id   = condition_id or f"cond-{uuid.uuid4().hex[:12]}",
            name           = name,
            field_path     = field_path,
            operator       = (
                ConditionOperator(operator) if isinstance(operator, str) else operator
            ),
            expected_value = expected_value,
            description    = description,
            metadata       = dict(metadata or {}),
            created_at     = datetime.now(timezone.utc).isoformat(),
        )

    # ── evaluation ────────────────────────────────────────────────────

    def evaluate(self, context_data: Dict[str, Any]) -> bool:
        """
        Evaluate this condition against a context data dict.

        Returns True when the condition passes.
        """
        actual = self._resolve_field(context_data)
        op     = self.operator

        if op == ConditionOperator.EXISTS:
            return actual is not None
        if op == ConditionOperator.NOT_EXISTS:
            return actual is None
        if actual is None:
            return False
        if op == ConditionOperator.EQUALS:
            return actual == self.expected_value
        if op == ConditionOperator.NOT_EQUALS:
            return actual != self.expected_value
        if op == ConditionOperator.IN:
            return actual in (self.expected_value or [])
        if op == ConditionOperator.NOT_IN:
            return actual not in (self.expected_value or [])
        if op == ConditionOperator.CONTAINS:
            return str(self.expected_value) in str(actual)
        if op == ConditionOperator.NOT_CONTAINS:
            return str(self.expected_value) not in str(actual)
        if op == ConditionOperator.GREATER_THAN:
            try:
                return float(actual) > float(self.expected_value)
            except (TypeError, ValueError):
                return False
        if op == ConditionOperator.LESS_THAN:
            try:
                return float(actual) < float(self.expected_value)
            except (TypeError, ValueError):
                return False
        return False

    def _resolve_field(self, data: Dict[str, Any]) -> Any:
        """Resolve a dot-notation field path against a nested dict."""
        parts: list = self.field_path.split(".")
        val: Any = data
        for part in parts:
            if not isinstance(val, dict):
                return None
            val = val.get(part)
        return val

    # ── serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id":   self.condition_id,
            "name":           self.name,
            "field_path":     self.field_path,
            "operator":       self.operator.value,
            "expected_value": self.expected_value,
            "description":    self.description,
            "metadata":       self.metadata,
            "created_at":     self.created_at,
        }
