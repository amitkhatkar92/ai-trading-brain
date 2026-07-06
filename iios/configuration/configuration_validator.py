"""
iios/configuration/configuration_validator.py
================================================
Schema-based validation for loaded configuration dictionaries.

``ConfigurationValidator`` accepts a map of ``SectionSchema`` objects and
validates a nested config dict against them. It returns a
``ValidationReport`` listing all errors and architectural warnings.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .configuration_constants import IIOS_ARCHITECTURE_CONSTANTS
from .configuration_exception import (
    FieldValidationError,
    SectionValidationError,
    ConfigurationValidationError,
)
from .configuration_schema import IIOS_SCHEMA, SectionSchema

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationValidator",
    "ValidationReport",
    "ValidationIssue",
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """One validation finding (error or warning)."""

    level: str          # "error" | "warning" | "info"
    section: str
    field: str
    message: str
    value: Any = None

    def __str__(self) -> str:
        loc = f"{self.section}.{self.field}" if self.field else self.section
        return f"[{self.level.upper()}] {loc}: {self.message}"


@dataclass
class ValidationReport:
    """Aggregated validation results."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, section: str, field_name: str, message: str, value: Any = None) -> None:
        self.issues.append(ValidationIssue("error", section, field_name, message, value))

    def add_warning(self, section: str, field_name: str, message: str, value: Any = None) -> None:
        self.issues.append(ValidationIssue("warning", section, field_name, message, value))

    def add_info(self, section: str, field_name: str, message: str) -> None:
        self.issues.append(ValidationIssue("info", section, field_name, message))

    def raise_if_invalid(self) -> None:
        """Raise ``SectionValidationError`` if there are any errors."""
        if not self.is_valid:
            errs = [
                FieldValidationError(i.section, i.field, i.message, i.value)
                for i in self.errors
            ]
            raise ConfigurationValidationError(
                f"Configuration validation failed with {len(errs)} error(s):\n"
                + "\n".join(f"  • {e}" for e in errs)
            )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class ConfigurationValidator:
    """Validates a nested configuration dictionary against the IIOS schema.

    Args:
        schema: Map of section name → ``SectionSchema``. Defaults to
                ``IIOS_SCHEMA`` if not provided.
        enforce_invariants: When ``True`` (default), a warning is emitted
            whenever an architecture-invariant constant differs from its
            certified value.
    """

    def __init__(
        self,
        schema: Optional[dict[str, SectionSchema]] = None,
        enforce_invariants: bool = True,
    ) -> None:
        self._schema = schema if schema is not None else IIOS_SCHEMA
        self._enforce_invariants = enforce_invariants

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, data: dict[str, Any]) -> ValidationReport:
        """Validate *data* against the registered schemas.

        Args:
            data: Nested dict keyed by section name (e.g. ``{"risk": {...}}``)
                  or dotted keys (``{"risk.vix_threshold": 45.0}``).

        Returns:
            ``ValidationReport`` with all findings.
        """
        # Normalise: both flat-dotted and nested forms accepted
        normalised = _to_nested(data)
        report = ValidationReport()

        # Per-section validation
        for section_name, schema in self._schema.items():
            section_data = normalised.get(section_name)
            if section_data is None:
                continue
            if not isinstance(section_data, dict):
                report.add_error(section_name, "", f"Section must be a dict, got {type(section_data).__name__}")
                continue

            field_errors = schema.validate(section_data)
            for exc in field_errors:
                report.add_error(exc.section, exc.field, str(exc.args[0]) if exc.args else str(exc), exc.field_value)

        # Architecture-invariant checks
        if self._enforce_invariants:
            self._check_invariants(normalised, report)

        # Log summary
        if report.errors:
            logger.error("Configuration validation: %d error(s)", len(report.errors))
            for err in report.errors:
                logger.error("  %s", err)
        if report.warnings:
            logger.warning("Configuration validation: %d warning(s)", len(report.warnings))
            for warn in report.warnings:
                logger.warning("  %s", warn)

        return report

    def validate_value(self, section: str, field_name: str, value: Any) -> ValidationReport:
        """Validate a single field value against its schema spec."""
        report = ValidationReport()
        schema = self._schema.get(section)
        if schema is None:
            report.add_warning(section, field_name, f"No schema registered for section {section!r}")
            return report
        spec = schema.fields.get(field_name)
        if spec is None:
            report.add_info(section, field_name, f"No spec for field {field_name!r}")
            return report
        try:
            spec.validate(value, section)
        except FieldValidationError as exc:
            report.add_error(exc.section, exc.field, str(exc.args[0]) if exc.args else str(exc), value)
        return report

    # ------------------------------------------------------------------
    # Architecture invariants
    # ------------------------------------------------------------------

    def _check_invariants(self, data: dict[str, Any], report: ValidationReport) -> None:
        """Warn if any architecture-invariant constant deviates from certified value."""
        for dotted_key, certified_value in IIOS_ARCHITECTURE_CONSTANTS.items():
            parts = dotted_key.split(".", 1)
            if len(parts) != 2:
                continue
            section_name, field_name = parts
            section = data.get(section_name)
            if not isinstance(section, dict):
                continue
            actual = section.get(field_name)
            if actual is None:
                continue
            if actual != certified_value:
                report.add_warning(
                    section_name, field_name,
                    f"Architecture constant deviates from certified value: "
                    f"{actual!r} != {certified_value!r} (FC-RULE-017/018)",
                    actual,
                )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_nested(data: dict[str, Any]) -> dict[str, Any]:
    """Convert a mix of nested dicts and dotted-key entries to a fully nested dict."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # Already nested section
            result.setdefault(key, {})
            result[key] = _merge_dicts(result[key], value)
        elif "." in key:
            parts = key.split(".", 1)
            section, field_name = parts[0], parts[1]
            result.setdefault(section, {})
            if isinstance(result[section], dict):
                result[section][field_name] = value
        else:
            result[key] = value
    return result


def _merge_dicts(base: dict, override: dict) -> dict:
    merged = dict(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _merge_dicts(merged[k], v)
        else:
            merged[k] = v
    return merged
