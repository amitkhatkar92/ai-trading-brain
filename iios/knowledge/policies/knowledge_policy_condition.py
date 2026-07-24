"""
knowledge_policy_condition.py — iios.knowledge.policies
---------------------------------------------------------
PolicyCondition — an atomic, evaluable governance condition.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict

from .constants import ConditionOperator


@dataclass(frozen=True)
class PolicyCondition:
    """
    An atomic condition that evaluates a single field in a knowledge artifact.

    All comparisons are value-based. No reasoning, no ML inference.
    Conditions are composed into PolicyRules using AND logic.
    """
    condition_id:   str
    name:           str
    field_path:     str               # dot-separated path, e.g. "metadata.source"
    operator:       ConditionOperator
    expected_value: Any
    description:    str

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:           str,
        field_path:     str,
        operator:       ConditionOperator,
        expected_value: Any = None,
        *,
        condition_id:   str = "",
        description:    str = "",
    ) -> "PolicyCondition":
        return cls(
            condition_id   = condition_id or f"cond-{uuid.uuid4().hex[:10]}",
            name           = name,
            field_path     = field_path,
            operator       = operator,
            expected_value = expected_value,
            description    = description,
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, artifact: Dict[str, Any]) -> bool:
        """
        Evaluate this condition against a knowledge artifact.

        Returns True if satisfied.  Never raises — returns False on error.
        """
        try:
            actual = self._resolve_field(artifact, self.field_path)
            return self._compare(actual)
        except Exception:
            return False

    def _resolve_field(self, artifact: Dict[str, Any], path: str) -> Any:
        parts = path.split(".")
        node: Any = artifact
        for part in parts:
            if isinstance(node, dict):
                node = node[part]
            else:
                raise KeyError(part)
        return node

    def _compare(self, actual: Any) -> bool:
        op = self.operator
        ev = self.expected_value
        if op == ConditionOperator.EQ:
            return actual == ev
        if op == ConditionOperator.NE:
            return actual != ev
        if op == ConditionOperator.GT:
            return actual > ev
        if op == ConditionOperator.LT:
            return actual < ev
        if op == ConditionOperator.GTE:
            return actual >= ev
        if op == ConditionOperator.LTE:
            return actual <= ev
        if op == ConditionOperator.CONTAINS:
            return ev in actual
        if op == ConditionOperator.NOT_CONTAINS:
            return ev not in actual
        if op == ConditionOperator.EXISTS:
            return actual is not None
        if op == ConditionOperator.NOT_EXISTS:
            return actual is None
        if op == ConditionOperator.IN_LIST:
            return actual in (ev or [])
        if op == ConditionOperator.NOT_IN_LIST:
            return actual not in (ev or [])
        return False

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id":   self.condition_id,
            "name":           self.name,
            "field_path":     self.field_path,
            "operator":       self.operator.value,
            "expected_value": self.expected_value,
            "description":    self.description,
        }
