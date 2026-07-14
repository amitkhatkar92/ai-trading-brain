"""iios/investment/strategy/integration/validation_report.py
ValidationReport: the output of a consistency validation pass.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.integration.integration_constants import ValidationStatus
from iios.investment.strategy.integration.consistency_rules import RuleCheckResult


@dataclass(frozen=True)
class ValidationCheck:
    """One validation check item (rule pass or fail)."""
    check_id:    str
    rule_id:     str
    rule_name:   str
    passed:      bool
    severity:    Optional[str]
    message:     str
    checked_at:  datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":   self.check_id,
            "rule_id":    self.rule_id,
            "rule_name":  self.rule_name,
            "passed":     self.passed,
            "severity":   self.severity,
            "message":    self.message,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass(frozen=True)
class ValidationReport:
    """Immutable output of one validation pass for one strategy."""
    report_id:          str
    strategy_id:        str
    status:             ValidationStatus
    checks_total:       int
    checks_passed:      int
    checks_failed:      int
    critical_conflicts: int
    high_conflicts:     int
    medium_conflicts:   int
    low_conflicts:      int
    completeness:       float    # 0–1
    consistency_score:  float    # 0–100
    checks:             Tuple[ValidationCheck, ...]
    warnings:           Tuple[str, ...]
    generated_at:       datetime

    @property
    def is_valid(self) -> bool:
        return self.status in (
            ValidationStatus.PASSED,
            ValidationStatus.PASSED_WITH_WARNINGS,
        )

    @property
    def pass_rate(self) -> float:
        if self.checks_total == 0:
            return 1.0
        return round(self.checks_passed / self.checks_total, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "strategy_id":        self.strategy_id,
            "status":             self.status.value,
            "is_valid":           self.is_valid,
            "checks_total":       self.checks_total,
            "checks_passed":      self.checks_passed,
            "checks_failed":      self.checks_failed,
            "critical_conflicts": self.critical_conflicts,
            "high_conflicts":     self.high_conflicts,
            "medium_conflicts":   self.medium_conflicts,
            "low_conflicts":      self.low_conflicts,
            "completeness":       round(self.completeness, 4),
            "consistency_score":  round(self.consistency_score, 2),
            "pass_rate":          round(self.pass_rate, 4),
            "warnings":           list(self.warnings),
            "generated_at":       self.generated_at.isoformat(),
        }


def build_validation_report(
    strategy_id:    str,
    check_results:  List[RuleCheckResult],
    completeness:   float,
    warnings:       Optional[List[str]] = None,
) -> ValidationReport:
    from iios.investment.strategy.integration.integration_constants import ConflictSeverity

    checks = tuple(
        ValidationCheck(
            check_id=str(uuid.uuid4()),
            rule_id=r.rule_id,
            rule_name=r.rule_name,
            passed=r.passed,
            severity=r.severity.value if r.severity else None,
            message=r.description,
            checked_at=r.checked_at,
        )
        for r in check_results
    )

    failed    = [r for r in check_results if not r.passed]
    passed_ct = len(check_results) - len(failed)

    crit = sum(1 for r in failed if r.severity == ConflictSeverity.CRITICAL)
    high = sum(1 for r in failed if r.severity == ConflictSeverity.HIGH)
    med  = sum(1 for r in failed if r.severity == ConflictSeverity.MEDIUM)
    low  = sum(1 for r in failed if r.severity == ConflictSeverity.LOW)

    # Consistency score: start at 100, deduct per conflict
    cons_score = 100.0
    for r in failed:
        if r.severity:
            cons_score -= r.severity.score_penalty
    cons_score = max(0.0, cons_score)

    if crit > 0:
        status = ValidationStatus.FAILED
    elif high > 0 or med > 0 or completeness < 0.5:
        status = ValidationStatus.PASSED_WITH_WARNINGS
    elif completeness < 0.2:
        status = ValidationStatus.INCOMPLETE
    else:
        status = ValidationStatus.PASSED

    return ValidationReport(
        report_id=str(uuid.uuid4()),
        strategy_id=strategy_id,
        status=status,
        checks_total=len(check_results),
        checks_passed=passed_ct,
        checks_failed=len(failed),
        critical_conflicts=crit,
        high_conflicts=high,
        medium_conflicts=med,
        low_conflicts=low,
        completeness=round(completeness, 4),
        consistency_score=round(cons_score, 2),
        checks=checks,
        warnings=tuple(warnings or []),
        generated_at=datetime.now(timezone.utc),
    )
