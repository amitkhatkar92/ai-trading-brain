"""iios/integration/validation/schema_validator.py

Validates DataRecord payloads against JSON-schema-like field specs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_constants import ValidationSeverity
from iios.integration.core.data_record import DataRecord
from iios.integration.validation.validation_report import ValidationIssue


@dataclass
class FieldSpec:
    """Specification for one field in a schema."""

    name:       str
    required:   bool  = False
    types:      tuple = ()         # Allowed Python types (empty = any)
    min_value:  Any   = None
    max_value:  Any   = None
    allowed:    list  = field(default_factory=list)  # Allowed values
    nullable:   bool  = True


class SchemaValidator:
    """
    Validates DataRecord payloads against a declared schema.
    """

    def __init__(self, specs: list[FieldSpec] | None = None) -> None:
        self._specs: dict[str, FieldSpec] = {}
        for s in (specs or []):
            self._specs[s.name] = s

    def add_field(self, spec: FieldSpec) -> None:
        self._specs[spec.name] = spec

    def validate_payload(
        self,
        record: DataRecord,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        payload = record.payload
        for name, spec in self._specs.items():
            value = payload.get(name)
            if value is None:
                if spec.required and not spec.nullable:
                    issues.append(ValidationIssue(
                        field_name=name,
                        message=f"Required field '{name}' is missing",
                        severity=ValidationSeverity.ERROR,
                        record_id=record.record_id,
                        rule="required_field",
                    ))
                continue
            if spec.types and not isinstance(value, spec.types):
                issues.append(ValidationIssue(
                    field_name=name,
                    message=f"Field '{name}' has wrong type: expected {spec.types}, got {type(value).__name__}",
                    severity=ValidationSeverity.ERROR,
                    record_id=record.record_id,
                    value=value,
                    rule="type_check",
                ))
            if spec.min_value is not None and value < spec.min_value:
                issues.append(ValidationIssue(
                    field_name=name,
                    message=f"Field '{name}' value {value} is below minimum {spec.min_value}",
                    severity=ValidationSeverity.ERROR,
                    record_id=record.record_id,
                    value=value,
                    rule="range_min",
                ))
            if spec.max_value is not None and value > spec.max_value:
                issues.append(ValidationIssue(
                    field_name=name,
                    message=f"Field '{name}' value {value} exceeds maximum {spec.max_value}",
                    severity=ValidationSeverity.ERROR,
                    record_id=record.record_id,
                    value=value,
                    rule="range_max",
                ))
            if spec.allowed and value not in spec.allowed:
                issues.append(ValidationIssue(
                    field_name=name,
                    message=f"Field '{name}' value {value!r} not in allowed set",
                    severity=ValidationSeverity.WARNING,
                    record_id=record.record_id,
                    value=value,
                    rule="allowed_values",
                ))
        return issues
