"""iios/decision_policies/compliance/compliance_validator.py"""
from __future__ import annotations

from ..policy_context import EvaluationContext
from .compliance_policy import CompliancePolicy, ComplianceResult


class ComplianceValidator:
    def validate_all(
        self,
        policies: list[CompliancePolicy],
        context:  EvaluationContext,
    ) -> list[ComplianceResult]:
        return [p.check(context) for p in policies if p.is_applicable(context)]

    def summary(self, results: list[ComplianceResult]) -> dict:
        total     = len(results)
        passed    = sum(1 for r in results if r.passed)
        violated  = sum(1 for r in results if r.violated)
        mandatory = sum(1 for r in results if r.blocks_decision)
        return {
            "total":              total,
            "passed":             passed,
            "violated":           violated,
            "mandatory_failures": mandatory,
            "blocked":            mandatory > 0,
        }
