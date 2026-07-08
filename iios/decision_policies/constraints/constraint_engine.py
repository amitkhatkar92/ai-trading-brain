"""iios/decision_policies/constraints/constraint_engine.py"""
from __future__ import annotations

from ..policy_context import EvaluationContext
from .constraint import Constraint
from .constraint_registry import ConstraintRegistry, get_constraint_registry
from .constraint_result import ConstraintResult
from .constraint_validator import ConstraintValidator


class ConstraintEngine:
    """Orchestrates constraint evaluation."""

    def __init__(self, registry: ConstraintRegistry | None = None) -> None:
        self._registry  = registry or get_constraint_registry()
        self._validator = ConstraintValidator()

    def evaluate(
        self,
        constraints: list[Constraint],
        context:     EvaluationContext,
    ) -> list[ConstraintResult]:
        return self._validator.validate_all(constraints, context)

    def evaluate_all_registered(
        self,
        context: EvaluationContext,
    ) -> list[ConstraintResult]:
        return self._validator.validate_all(self._registry.all(), context)

    def summary(self, results: list[ConstraintResult]) -> dict:
        return self._validator.summary(results)

    def has_hard_violations(self, results: list[ConstraintResult]) -> bool:
        return any(r.blocks_decision for r in results)
