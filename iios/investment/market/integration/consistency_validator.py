"""iios/investment/market/integration/consistency_validator.py
Runs all consistency rules against AggregationState → ValidationReport.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.consistency_rules import (
    BUILT_IN_RULES,
    ConsistencyRule,
)
from iios.investment.market.integration.models import (
    ConflictSeverity,
    ValidationIssue,
    ValidationReport,
    ValidationStatus,
)

log = logging.getLogger(__name__)

_SEVERITY_ORDER = {
    ConflictSeverity.LOW:      0,
    ConflictSeverity.MEDIUM:   1,
    ConflictSeverity.HIGH:     2,
    ConflictSeverity.CRITICAL: 3,
}


def _worst(a: ConflictSeverity, b: ConflictSeverity) -> ConflictSeverity:
    return a if _SEVERITY_ORDER[a] >= _SEVERITY_ORDER[b] else b


class ConsistencyValidator:
    """Evaluates a set of ConsistencyRules against an AggregationState.

    Custom rules can be injected at construction time; they are merged with
    BUILT_IN_RULES for evaluation.
    """

    def __init__(self, extra_rules: Optional[List[ConsistencyRule]] = None) -> None:
        self._rules: List[ConsistencyRule] = list(BUILT_IN_RULES)
        if extra_rules:
            self._rules.extend(extra_rules)

    def add_rule(self, rule: ConsistencyRule) -> None:
        self._rules.append(rule)

    @property
    def rules(self) -> List[ConsistencyRule]:
        return list(self._rules)

    def validate(self, state: AggregationState) -> ValidationReport:
        issues:  List[ValidationIssue] = []
        passed   = 0
        failed   = 0
        warned   = 0

        for rule in self._rules:
            try:
                triggered = rule.check(state)
            except Exception:
                log.exception("rule %s raised during check", rule.name)
                triggered = False

            if triggered:
                issue = ValidationIssue(
                    rule_name=rule.name,
                    conflict_type=rule.conflict_type,
                    severity=rule.severity,
                    description=rule.description,
                    engines_involved=list(rule.engines),
                )
                issues.append(issue)
                if rule.severity in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL):
                    failed += 1
                else:
                    warned += 1
            else:
                passed += 1

        # Determine overall status from worst severity
        status = ValidationStatus.PASSED
        if issues:
            worst = max(issues, key=lambda i: _SEVERITY_ORDER[i.severity]).severity
            if worst in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL):
                status = ValidationStatus.FAILED
            else:
                status = ValidationStatus.WARNING

        return ValidationReport(
            bar_index=state.bar_index,
            status=status,
            issues=issues,
            passed_rules=passed,
            failed_rules=failed,
            warned_rules=warned,
        )
