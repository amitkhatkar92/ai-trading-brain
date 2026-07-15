"""iios/investment/portfolio/rebalancing/validation_report.py

Validation result types for rebalancing plans.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.rebalancing.rebalancing_types import ValidationStatus


@dataclass(frozen=True)
class ValidationCheck:
    """Result of a single validation check."""

    check_id:    str
    description: str
    status:      ValidationStatus = ValidationStatus.PASSED
    detail:      str = ""
    severity:    str = "info"   # info / warning / error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":   self.check_id,
            "status":     self.status.value,
            "description":self.description,
            "detail":     self.detail,
            "severity":   self.severity,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Complete validation report for a rebalancing plan."""

    report_id:       str                = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str                = ""

    overall_status:  ValidationStatus   = ValidationStatus.PASSED
    is_valid:        bool               = True
    checks:          tuple              = field(default_factory=tuple)  # ValidationCheck

    # Summary counts
    n_passed:        int                = 0
    n_warnings:      int                = 0
    n_failed:        int                = 0

    primary_failure: str                = ""
    warnings:        tuple              = field(default_factory=tuple)  # str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "is_valid":        self.is_valid,
            "n_passed":        self.n_passed,
            "n_warnings":      self.n_warnings,
            "n_failed":        self.n_failed,
            "primary_failure": self.primary_failure,
            "checks":          [c.to_dict() for c in self.checks],
        }


def build_validation_report(
    checks:       List[ValidationCheck],
    portfolio_id: str = "",
) -> ValidationReport:
    """Aggregate individual checks into a ValidationReport."""
    n_passed   = sum(1 for c in checks if c.status == ValidationStatus.PASSED)
    n_warnings = sum(1 for c in checks if c.status == ValidationStatus.WARNING)
    n_failed   = sum(1 for c in checks if c.status == ValidationStatus.FAILED)

    is_valid = n_failed == 0

    failed_checks = [c for c in checks if c.status == ValidationStatus.FAILED]
    primary_failure = failed_checks[0].detail if failed_checks else ""

    if n_failed > 0:
        overall = ValidationStatus.FAILED
    elif n_warnings > 0:
        overall = ValidationStatus.WARNING
    else:
        overall = ValidationStatus.PASSED

    warning_texts = tuple(c.detail for c in checks if c.status == ValidationStatus.WARNING)

    return ValidationReport(
        portfolio_id    = portfolio_id,
        overall_status  = overall,
        is_valid        = is_valid,
        checks          = tuple(checks),
        n_passed        = n_passed,
        n_warnings      = n_warnings,
        n_failed        = n_failed,
        primary_failure = primary_failure,
        warnings        = warning_texts,
    )
