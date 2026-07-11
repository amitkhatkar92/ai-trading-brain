"""iios/investment/market/integration/validation_report.py
Builder helpers for ValidationReport — convenience layer used by the engine.
"""
from __future__ import annotations

from typing import List

from iios.investment.market.integration.models import (
    ConflictSeverity,
    ValidationIssue,
    ValidationReport,
    ValidationStatus,
)

_ORDER = {
    ConflictSeverity.LOW: 0, ConflictSeverity.MEDIUM: 1,
    ConflictSeverity.HIGH: 2, ConflictSeverity.CRITICAL: 3,
}


class ValidationReportBuilder:
    """Assembles a ValidationReport from a list of issues."""

    @staticmethod
    def build(issues: List[ValidationIssue], bar_index: int) -> ValidationReport:
        if not issues:
            return ValidationReport(bar_index=bar_index, status=ValidationStatus.PASSED)

        worst = max(issues, key=lambda i: _ORDER[i.severity]).severity
        if worst in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL):
            status = ValidationStatus.FAILED
        else:
            status = ValidationStatus.WARNING

        failed  = sum(1 for i in issues if i.severity in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL))
        warned  = len(issues) - failed

        return ValidationReport(
            bar_index=bar_index,
            status=status,
            issues=list(issues),
            failed_rules=failed,
            warned_rules=warned,
        )
