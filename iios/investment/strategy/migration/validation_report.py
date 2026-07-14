"""iios/investment/strategy/migration/validation_report.py
Validation result types for migration compatibility checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationCheckType(str, Enum):
    """Category of a validation check."""
    LIFECYCLE    = "lifecycle"
    CONFIGURATION = "configuration"
    SIGNAL       = "signal"
    RISK         = "risk"
    EXECUTION    = "execution"
    DEPENDENCY   = "dependency"
    PERFORMANCE  = "performance"
    BEHAVIOR     = "behavior"


class CheckSeverity(str, Enum):
    PASS    = "pass"
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"
    FATAL   = "fatal"

    @property
    def blocks_migration(self) -> bool:
        return self in (CheckSeverity.ERROR, CheckSeverity.FATAL)


@dataclass(frozen=True)
class ValidationCheck:
    """Result of a single validation check."""
    check_id:    str
    check_type:  ValidationCheckType
    name:        str
    severity:    CheckSeverity
    message:     str
    detail:      str = ""
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":    self.check_id,
            "check_type":  self.check_type.value,
            "name":        self.name,
            "severity":    self.severity.value,
            "message":     self.message,
            "detail":      self.detail,
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class ValidationReport:
    """
    Aggregated validation report for a single strategy migration.
    Immutable — created once after validation is complete.
    """
    strategy_id:   str
    strategy_name: str
    validated_at:  datetime
    duration_ms:   float

    checks:        List[ValidationCheck]
    passed_count:  int
    warning_count: int
    error_count:   int
    fatal_count:   int

    is_migration_approved: bool     # True if no blocking issues
    compatibility_level:   str      # full / partial / requires_adapter / incompatible
    interface_gaps:        List[str]
    recommendations:       List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":          self.strategy_id,
            "strategy_name":        self.strategy_name,
            "validated_at":         self.validated_at.isoformat(),
            "duration_ms":          round(self.duration_ms, 2),
            "is_migration_approved": self.is_migration_approved,
            "compatibility_level":  self.compatibility_level,
            "passed_count":         self.passed_count,
            "warning_count":        self.warning_count,
            "error_count":          self.error_count,
            "fatal_count":          self.fatal_count,
            "interface_gaps":       self.interface_gaps,
            "recommendations":      self.recommendations,
            "checks":               [c.to_dict() for c in self.checks],
        }

    @property
    def has_blocking_issues(self) -> bool:
        return self.error_count > 0 or self.fatal_count > 0

    @property
    def has_warnings(self) -> bool:
        return self.warning_count > 0


def build_validation_report(
    strategy_id:   str,
    strategy_name: str,
    checks:        List[ValidationCheck],
    gaps:          List[str],
    duration_ms:   float,
) -> ValidationReport:
    """Construct a ValidationReport from individual checks."""
    passed  = sum(1 for c in checks if c.severity == CheckSeverity.PASS)
    warnings = sum(1 for c in checks if c.severity == CheckSeverity.WARNING)
    errors  = sum(1 for c in checks if c.severity == CheckSeverity.ERROR)
    fatals  = sum(1 for c in checks if c.severity == CheckSeverity.FATAL)

    has_blocking = errors > 0 or fatals > 0

    # Determine compatibility level
    if has_blocking:
        compat = "incompatible"
    elif gaps:
        compat = "requires_adapter"
    elif warnings:
        compat = "partial"
    else:
        compat = "full"

    # Gather recommendations
    recommendations = [
        c.remediation for c in checks
        if c.remediation and c.severity in (CheckSeverity.WARNING, CheckSeverity.ERROR)
    ]

    return ValidationReport(
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        validated_at=datetime.now(timezone.utc),
        duration_ms=duration_ms,
        checks=checks,
        passed_count=passed,
        warning_count=warnings,
        error_count=errors,
        fatal_count=fatals,
        is_migration_approved=not has_blocking,
        compatibility_level=compat,
        interface_gaps=gaps,
        recommendations=list(set(recommendations)),
    )
