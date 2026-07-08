"""iios/decision_governance/compliance/compliance_checker.py

ComplianceChecker — pluggable compliance rule evaluation.
Rules are callables: (GovernanceSubject) -> ComplianceViolation | None
"""
from __future__ import annotations

from typing import Callable

from iios.decision_governance.governance_context import GovernanceSubject
from iios.decision_governance.compliance.compliance_result import (
    ComplianceResult,
    ComplianceViolation,
)


ComplianceRule = Callable[[GovernanceSubject], "ComplianceViolation | None"]


class ComplianceChecker:
    """Runs compliance rules against a GovernanceSubject."""

    def __init__(self) -> None:
        self._rules: list[tuple[str, str, ComplianceRule, bool]] = []
        # (rule_id, rule_name, callable, is_blocking)

    def add_rule(
        self,
        rule_id:     str,
        rule_name:   str,
        rule:        ComplianceRule,
        is_blocking: bool = True,
    ) -> "ComplianceChecker":
        self._rules.append((rule_id, rule_name, rule, is_blocking))
        return self

    def check(self, subject: GovernanceSubject) -> ComplianceResult:
        violations: list[ComplianceViolation] = []

        for rule_id, rule_name, rule, is_blocking in self._rules:
            try:
                violation = rule(subject)
            except Exception as exc:  # noqa: BLE001
                violation = ComplianceViolation(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    message=f"Rule execution error: {exc}",
                    is_blocking=is_blocking,
                )
            if violation is not None:
                violation.rule_id     = rule_id
                violation.rule_name   = rule_name
                violation.is_blocking = is_blocking
                violations.append(violation)

        blocking = any(v.is_blocking for v in violations)
        return ComplianceResult(
            subject_id=subject.subject_id,
            rules_checked=len(self._rules),
            violations=violations,
            passed=not blocking,
        )
