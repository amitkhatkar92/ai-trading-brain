"""iios/integration/validation/validation_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_constants import ValidationSeverity, ValidationStatus
from iios.integration.core.data_record import DataRecord


@dataclass
class ValidationIssue:
    """One problem found during validation."""

    field_name:  str               = ""
    message:     str               = ""
    severity:    ValidationSeverity = ValidationSeverity.ERROR
    record_id:   str               = ""
    value:       Any               = None
    rule:        str               = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "message":    self.message,
            "severity":   self.severity.value,
            "record_id":  self.record_id,
            "rule":       self.rule,
        }


@dataclass
class ValidationReport:
    """Aggregate result of validating a batch of DataRecords."""

    provider_id:    str              = ""
    total:          int              = 0
    valid_count:    int              = 0
    invalid_count:  int              = 0
    skipped_count:  int              = 0
    status:         ValidationStatus = ValidationStatus.PASSED
    issues:         list[ValidationIssue] = field(default_factory=list)
    valid_records:  list[DataRecord]  = field(default_factory=list)
    invalid_records: list[DataRecord] = field(default_factory=list)
    quality_score:  float            = 1.0
    report_id:      str              = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at:   float            = field(default_factory=time.time)
    metadata:       dict[str, Any]   = field(default_factory=dict)

    def pass_rate(self) -> float:
        return self.valid_count / self.total if self.total > 0 else 1.0

    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":     self.report_id,
            "provider_id":   self.provider_id,
            "total":         self.total,
            "valid_count":   self.valid_count,
            "invalid_count": self.invalid_count,
            "skipped_count": self.skipped_count,
            "status":        self.status.value,
            "pass_rate":     round(self.pass_rate(), 4),
            "quality_score": round(self.quality_score, 4),
            "error_count":   self.error_count(),
            "warning_count": self.warning_count(),
            "generated_at":  self.generated_at,
        }
