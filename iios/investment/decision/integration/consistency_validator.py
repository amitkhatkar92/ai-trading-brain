"""iios/investment/decision/integration/consistency_validator.py
ConsistencyValidator — runs all applicable consistency rules against a
given AggregationStateSnapshot and returns a ValidationReport.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot
from iios.investment.decision.integration.consistency_rules import (
    DEFAULT_RULES,
    ConsistencyRule,
)
from iios.investment.decision.integration.validation_report import (
    ValidationCheck,
    ValidationReport,
    build_validation_report,
)


class ConsistencyValidator:
    """
    Stateless validator.  Runs a pluggable list of ConsistencyRules against
    a snapshot and returns a ValidationReport.  Rules are skipped (not
    reported as failures) when their required components are absent.
    """

    def __init__(self, rules: Optional[List[ConsistencyRule]] = None) -> None:
        self._rules: List[ConsistencyRule] = rules if rules is not None else list(DEFAULT_RULES)

    def validate(self, snap: _AggregationStateSnapshot) -> ValidationReport:
        checks: List[ValidationCheck] = []
        for rule in self._rules:
            result = rule.check(snap)
            if result is not None:
                checks.append(result)
        decision_id = getattr(snap, "decision_id", "")
        subject_id  = getattr(snap, "subject_id",  "")
        return build_validation_report(decision_id, subject_id, checks)

    def add_rule(self, rule: ConsistencyRule) -> None:
        self._rules.append(rule)

    @property
    def rule_count(self) -> int:
        return len(self._rules)
