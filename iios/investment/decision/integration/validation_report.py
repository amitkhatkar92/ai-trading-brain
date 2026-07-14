"""iios/investment/decision/integration/validation_report.py
Types for consistency validation results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from iios.investment.decision.integration.integration_constants import ValidationStatus


@dataclass(frozen=True)
class ValidationCheck:
    """Result of a single consistency check."""
    check_id:    str
    rule_id:     str
    rule_name:   str
    status:      ValidationStatus
    message:     str
    detail:      Optional[str] = None
    component_a: Optional[str] = None
    component_b: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":    self.check_id,
            "rule_id":     self.rule_id,
            "rule_name":   self.rule_name,
            "status":      self.status.value,
            "message":     self.message,
            "detail":      self.detail,
            "component_a": self.component_a,
            "component_b": self.component_b,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Aggregated result of all consistency checks for one decision."""
    report_id:       str
    decision_id:     str
    subject_id:      str
    overall_status:  ValidationStatus
    checks:          Tuple[ValidationCheck, ...]
    valid_count:     int
    warning_count:   int
    invalid_count:   int
    blocking_count:  int           # checks with INVALID status
    created_at:      datetime

    @property
    def is_valid(self) -> bool:
        return self.overall_status != ValidationStatus.INVALID

    @property
    def has_warnings(self) -> bool:
        return self.warning_count > 0

    @property
    def invalid_checks(self) -> List[ValidationCheck]:
        return [c for c in self.checks if c.status == ValidationStatus.INVALID]

    @property
    def warning_checks(self) -> List[ValidationCheck]:
        return [c for c in self.checks if c.status == ValidationStatus.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":      self.report_id,
            "decision_id":    self.decision_id,
            "subject_id":     self.subject_id,
            "overall_status": self.overall_status.value,
            "is_valid":       self.is_valid,
            "valid_count":    self.valid_count,
            "warning_count":  self.warning_count,
            "invalid_count":  self.invalid_count,
            "blocking_count": self.blocking_count,
            "checks":         [c.to_dict() for c in self.checks],
            "created_at":     self.created_at.isoformat(),
        }


def _make_check(
    rule_id:     str,
    rule_name:   str,
    status:      ValidationStatus,
    message:     str,
    detail:      Optional[str] = None,
    component_a: Optional[str] = None,
    component_b: Optional[str] = None,
) -> ValidationCheck:
    return ValidationCheck(
        check_id    = str(uuid.uuid4()),
        rule_id     = rule_id,
        rule_name   = rule_name,
        status      = status,
        message     = message,
        detail      = detail,
        component_a = component_a,
        component_b = component_b,
    )


def build_validation_report(
    decision_id: str,
    subject_id:  str,
    checks:      List[ValidationCheck],
) -> ValidationReport:
    valid_count   = sum(1 for c in checks if c.status == ValidationStatus.VALID)
    warning_count = sum(1 for c in checks if c.status == ValidationStatus.WARNING)
    invalid_count = sum(1 for c in checks if c.status == ValidationStatus.INVALID)
    blocking      = invalid_count

    if invalid_count > 0:
        overall = ValidationStatus.INVALID
    elif warning_count > 0:
        overall = ValidationStatus.WARNING
    else:
        overall = ValidationStatus.VALID

    return ValidationReport(
        report_id      = str(uuid.uuid4()),
        decision_id    = decision_id,
        subject_id     = subject_id,
        overall_status = overall,
        checks         = tuple(checks),
        valid_count    = valid_count,
        warning_count  = warning_count,
        invalid_count  = invalid_count,
        blocking_count = blocking,
        created_at     = datetime.now(timezone.utc),
    )
