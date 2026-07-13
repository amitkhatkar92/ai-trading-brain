"""iios/investment/company/integration/validation_report.py
ValidationReport and ValidationCheck dataclasses.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.company_state import (
    ConflictSeverity, ValidationStatus,
)


@dataclass
class ValidationCheck:
    """
    Result of a single consistency check between two intelligence dimensions.
    """
    name:         str
    description:  str
    status:       ValidationStatus
    engine_a:     str
    engine_b:     str
    value_a:      Optional[float]
    value_b:      Optional[float]
    message:      str
    severity:     ConflictSeverity = ConflictSeverity.INFO

    @property
    def is_failed(self) -> bool:
        return self.status == ValidationStatus.FAILED

    @property
    def is_warning(self) -> bool:
        return self.status == ValidationStatus.WARNING

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":        self.name,
            "description": self.description,
            "status":      self.status.value,
            "engine_a":    self.engine_a,
            "engine_b":    self.engine_b,
            "value_a":     round(self.value_a, 1) if self.value_a is not None else None,
            "value_b":     round(self.value_b, 1) if self.value_b is not None else None,
            "message":     self.message,
            "severity":    self.severity.value,
        }


@dataclass
class ValidationReport:
    """
    Aggregated result of all consistency checks for a single ticker evaluation.
    """
    report_id:     str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    ticker:        str = ""
    generated_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    checks:        List[ValidationCheck] = field(default_factory=list)

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.is_warning)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if c.is_failed)

    @property
    def critical_failure_count(self) -> int:
        return sum(
            1 for c in self.checks
            if c.is_failed and c.severity == ConflictSeverity.CRITICAL
        )

    @property
    def validation_passed(self) -> bool:
        """True if no CRITICAL failures and at most 2 WARNING checks."""
        return self.critical_failure_count == 0 and self.failed_count == 0

    @property
    def consistency_fraction(self) -> float:
        """Fraction of checks that PASSED (0-1)."""
        if self.total_checks == 0:
            return 1.0
        return self.passed_count / self.total_checks

    def failed_checks(self) -> List[ValidationCheck]:
        return [c for c in self.checks if c.is_failed]

    def warning_checks(self) -> List[ValidationCheck]:
        return [c for c in self.checks if c.is_warning]

    def messages(self) -> List[str]:
        """All non-passing check messages."""
        return [c.message for c in self.checks if not c.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":             self.report_id,
            "ticker":                self.ticker,
            "generated_at":          self.generated_at.isoformat(),
            "total_checks":          self.total_checks,
            "passed":                self.passed_count,
            "warnings":              self.warning_count,
            "failures":              self.failed_count,
            "critical_failures":     self.critical_failure_count,
            "validation_passed":     self.validation_passed,
            "consistency_fraction":  round(self.consistency_fraction, 3),
            "checks":                [c.to_dict() for c in self.checks],
        }
