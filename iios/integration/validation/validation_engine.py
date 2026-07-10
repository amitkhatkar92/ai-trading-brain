"""iios/integration/validation/validation_engine.py

Orchestrates all validation steps for a batch of DataRecords.
"""
from __future__ import annotations

import logging
from typing import Any

from iios.integration.integration_constants import ValidationSeverity, ValidationStatus
from iios.integration.core.data_record import DataRecord
from iios.integration.validation.integrity_checker import IntegrityChecker
from iios.integration.validation.quality_checker import QualityChecker
from iios.integration.validation.schema_validator import SchemaValidator
from iios.integration.validation.validation_report import ValidationIssue, ValidationReport

logger = logging.getLogger(__name__)


class ValidationEngine:
    """
    Runs schema validation, integrity checks, and quality scoring
    against a batch of DataRecords.
    """

    def __init__(
        self,
        schema_validator:  SchemaValidator  | None = None,
        integrity_checker: IntegrityChecker | None = None,
        quality_checker:   QualityChecker   | None = None,
        min_quality_score: float            = 0.0,
    ) -> None:
        self._schema    = schema_validator  or SchemaValidator()
        self._integrity = integrity_checker or IntegrityChecker()
        self._quality   = quality_checker   or QualityChecker()
        self._min_score = min_quality_score

    def validate_record(self, record: DataRecord) -> list[ValidationIssue]:
        return self._schema.validate_payload(record)

    def validate_batch(self, records: list[DataRecord]) -> ValidationReport:
        report = ValidationReport(
            provider_id=records[0].provider_id if records else "",
            total=len(records),
        )
        all_issues: list[ValidationIssue] = []
        valid:   list[DataRecord] = []
        invalid: list[DataRecord] = []

        # Per-record schema validation
        for rec in records:
            issues = self._schema.validate_payload(rec)
            errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
            all_issues.extend(issues)
            if errors:
                invalid.append(rec)
            else:
                valid.append(rec)

        # Batch-level integrity
        integrity_issues = self._integrity.check_duplicates(records)
        integrity_issues += self._integrity.check_ohlcv_consistency(valid)
        all_issues.extend(integrity_issues)

        # Quality scoring
        avg_score = self._quality.batch_avg_score(valid) if valid else 0.0

        report.valid_count    = len(valid)
        report.invalid_count  = len(invalid)
        report.valid_records  = valid
        report.invalid_records = invalid
        report.issues         = all_issues
        report.quality_score  = avg_score
        report.status = (
            ValidationStatus.PASSED if not invalid
            else ValidationStatus.PARTIAL if valid
            else ValidationStatus.FAILED
        )
        return report

    def statistics(self) -> dict[str, Any]:
        return {
            "min_quality_score": self._min_score,
        }
