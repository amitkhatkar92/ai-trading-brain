"""iios/decision_policies/compliance/compliance_engine.py"""
from __future__ import annotations

import threading

from ..policy_context import EvaluationContext
from .compliance_policy import CompliancePolicy, ComplianceResult
from .compliance_report import ComplianceReport, build_compliance_report
from .compliance_validator import ComplianceValidator


class ComplianceEngine:
    """Orchestrates compliance policy evaluation."""

    def __init__(self) -> None:
        self._policies: list[CompliancePolicy] = []
        self._validator = ComplianceValidator()
        self._lock      = threading.RLock()

    def register(self, policy: CompliancePolicy) -> None:
        with self._lock:
            self._policies.append(policy)

    def unregister(self, policy_id: str) -> bool:
        with self._lock:
            before = len(self._policies)
            self._policies = [p for p in self._policies if p.policy_id != policy_id]
            return len(self._policies) < before

    def evaluate(
        self,
        context:  EvaluationContext,
        *,
        policies: list[CompliancePolicy] | None = None,
    ) -> ComplianceReport:
        with self._lock:
            target = list(policies if policies is not None else self._policies)
        results = self._validator.validate_all(target, context)
        return build_compliance_report(
            results,
            context_id = context.context_id,
            source_id  = context.source_id,
        )

    def all_policies(self) -> list[CompliancePolicy]:
        with self._lock:
            return list(self._policies)

    def policy_count(self) -> int:
        with self._lock:
            return len(self._policies)
