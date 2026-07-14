"""iios/investment/portfolio/construction/validation_report.py

Validation finding and report types used across all validators.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    ValidationCategory,
    ValidationOutcome,
)


@dataclass(frozen=True)
class ValidationFinding:
    """A single finding from any validation check."""

    finding_id:   str                = field(default_factory=lambda: str(uuid.uuid4()))
    category:     ValidationCategory = ValidationCategory.INTEGRITY
    outcome:      ValidationOutcome  = ValidationOutcome.PASSED
    rule:         str                = ""
    message:      str                = ""
    symbol:       str                = ""   # empty when not symbol-specific
    field_name:   str                = ""   # empty when not field-specific
    actual:       Any                = None
    expected:     Any                = None
    checked_at:   float              = field(default_factory=time.time)
    details:      Dict[str, Any]     = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.outcome == ValidationOutcome.PASSED

    @property
    def is_warning(self) -> bool:
        return self.outcome == ValidationOutcome.WARNING

    @property
    def is_blocking(self) -> bool:
        return self.outcome == ValidationOutcome.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category":   self.category.value,
            "outcome":    self.outcome.value,
            "rule":       self.rule,
            "message":    self.message,
            "symbol":     self.symbol,
            "field_name": self.field_name,
            "actual":     self.actual,
            "expected":   self.expected,
            "checked_at": self.checked_at,
            "details":    dict(self.details),
        }


# ---------------------------------------------------------------------------
# Helpers to create standard findings
# ---------------------------------------------------------------------------

def _pass(
    category: ValidationCategory,
    rule: str,
    message: str = "",
    **kwargs: Any,
) -> ValidationFinding:
    return ValidationFinding(
        category=category,
        outcome=ValidationOutcome.PASSED,
        rule=rule,
        message=message or f"{rule}: passed",
        **kwargs,
    )


def _warn(
    category: ValidationCategory,
    rule: str,
    message: str,
    **kwargs: Any,
) -> ValidationFinding:
    return ValidationFinding(
        category=category,
        outcome=ValidationOutcome.WARNING,
        rule=rule,
        message=message,
        **kwargs,
    )


def _fail(
    category: ValidationCategory,
    rule: str,
    message: str,
    **kwargs: Any,
) -> ValidationFinding:
    return ValidationFinding(
        category=category,
        outcome=ValidationOutcome.FAILED,
        rule=rule,
        message=message,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationReport:
    """
    Aggregate report produced by one or more validators.

    is_valid is True when no FAILED findings exist.
    has_warnings is True when at least one WARNING finding exists.
    """

    report_id:     str                          = field(default_factory=lambda: str(uuid.uuid4()))
    validator:     str                          = ""
    blueprint_id:  str                          = ""
    portfolio_id:  str                          = ""

    findings:      Tuple[ValidationFinding, ...] = field(default_factory=tuple)

    # Counts
    total:         int                          = 0
    passed:        int                          = 0
    warnings:      int                          = 0
    failures:      int                          = 0

    # Verdict
    is_valid:      bool                         = True
    has_warnings:  bool                         = False

    validated_at:  float                        = field(default_factory=time.time)
    duration_ms:   float                        = 0.0

    @property
    def failed_findings(self) -> Tuple[ValidationFinding, ...]:
        return tuple(f for f in self.findings if f.is_blocking)

    @property
    def warning_findings(self) -> Tuple[ValidationFinding, ...]:
        return tuple(f for f in self.findings if f.is_warning)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":    self.report_id,
            "validator":    self.validator,
            "blueprint_id": self.blueprint_id,
            "portfolio_id": self.portfolio_id,
            "total":        self.total,
            "passed":       self.passed,
            "warnings":     self.warnings,
            "failures":     self.failures,
            "is_valid":     self.is_valid,
            "has_warnings": self.has_warnings,
            "pass_rate":    round(self.pass_rate, 4),
            "duration_ms":  round(self.duration_ms, 2),
            "validated_at": self.validated_at,
            "findings":     [f.to_dict() for f in self.findings],
        }


def build_report(
    findings: List[ValidationFinding],
    *,
    validator: str,
    blueprint_id: str = "",
    portfolio_id: str = "",
    duration_ms: float = 0.0,
) -> ValidationReport:
    """Construct a ValidationReport from a list of findings."""
    total    = len(findings)
    passed   = sum(1 for f in findings if f.passed)
    warnings = sum(1 for f in findings if f.is_warning)
    failures = sum(1 for f in findings if f.is_blocking)
    return ValidationReport(
        validator=validator,
        blueprint_id=blueprint_id,
        portfolio_id=portfolio_id,
        findings=tuple(findings),
        total=total,
        passed=passed,
        warnings=warnings,
        failures=failures,
        is_valid=failures == 0,
        has_warnings=warnings > 0,
        duration_ms=duration_ms,
    )
