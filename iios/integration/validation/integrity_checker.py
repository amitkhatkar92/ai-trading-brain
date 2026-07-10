"""iios/integration/validation/integrity_checker.py

Checks for duplicate records and cross-record consistency.
"""
from __future__ import annotations

from typing import Any

from iios.integration.integration_constants import ValidationSeverity
from iios.integration.core.data_record import DataRecord
from iios.integration.validation.validation_report import ValidationIssue


class IntegrityChecker:
    """
    Detects duplicate records and consistency violations within a batch.
    """

    def __init__(
        self,
        duplicate_key_fields: list[str] | None = None,
    ) -> None:
        # Fields that together form a "logical key" for deduplication
        self._key_fields = duplicate_key_fields or ["symbol", "timestamp"]

    def _record_key(self, record: DataRecord) -> tuple:
        payload = record.payload
        return tuple(payload.get(f) for f in self._key_fields)

    def check_duplicates(
        self,
        records: list[DataRecord],
    ) -> list[ValidationIssue]:
        seen:   dict[tuple, str] = {}
        issues: list[ValidationIssue] = []
        for rec in records:
            key = self._record_key(rec)
            if key in seen:
                issues.append(ValidationIssue(
                    field_name="_duplicate",
                    message=f"Duplicate record: key={key} first_seen={seen[key]}",
                    severity=ValidationSeverity.WARNING,
                    record_id=rec.record_id,
                    rule="duplicate_key",
                ))
            else:
                seen[key] = rec.record_id
        return issues

    def check_ohlcv_consistency(
        self,
        records: list[DataRecord],
    ) -> list[ValidationIssue]:
        """
        For market data records, validate that:
        - low ≤ close ≤ high
        - low ≤ open ≤ high
        - volume ≥ 0
        """
        issues: list[ValidationIssue] = []
        for rec in records:
            p   = rec.payload
            low  = p.get("low")
            high = p.get("high")
            open_ = p.get("open")
            close = p.get("close")
            volume = p.get("volume")
            if None in (low, high):
                continue
            if low > high:
                issues.append(ValidationIssue(
                    field_name="low/high",
                    message=f"low ({low}) > high ({high})",
                    severity=ValidationSeverity.ERROR,
                    record_id=rec.record_id,
                    rule="ohlcv_consistency",
                ))
            for field_name, value in [("open", open_), ("close", close)]:
                if value is not None and (value < low or value > high):
                    issues.append(ValidationIssue(
                        field_name=field_name,
                        message=f"{field_name} ({value}) outside low-high range [{low},{high}]",
                        severity=ValidationSeverity.WARNING,
                        record_id=rec.record_id,
                        rule="ohlcv_range",
                    ))
            if volume is not None and volume < 0:
                issues.append(ValidationIssue(
                    field_name="volume",
                    message=f"Negative volume: {volume}",
                    severity=ValidationSeverity.ERROR,
                    record_id=rec.record_id,
                    rule="volume_negative",
                ))
        return issues
