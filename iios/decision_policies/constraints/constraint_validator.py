"""iios/decision_policies/constraints/constraint_validator.py"""
from __future__ import annotations

from ..policy_context import EvaluationContext
from .constraint import Constraint
from .constraint_result import ConstraintResult


class ConstraintValidator:
    """Validates a list of constraints against an EvaluationContext."""

    def validate_all(
        self,
        constraints: list[Constraint],
        context:     EvaluationContext,
    ) -> list[ConstraintResult]:
        return [c.validate(context) for c in constraints if c.is_applicable(context)]

    def summary(self, results: list[ConstraintResult]) -> dict:
        total     = len(results)
        passed    = sum(1 for r in results if r.passed)
        violated  = sum(1 for r in results if r.violated)
        hard_viol = sum(1 for r in results if r.blocks_decision)
        soft_warn = sum(1 for r in results if r.violated and not r.is_hard)
        return {
            "total":           total,
            "passed":          passed,
            "violated":        violated,
            "hard_violations": hard_viol,
            "soft_warnings":   soft_warn,
            "blocked":         hard_viol > 0,
        }
