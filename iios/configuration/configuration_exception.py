"""
iios/configuration/configuration_exception.py
===============================================
Exception hierarchy for the IIOS Configuration Management System.

All exceptions are structured with machine-readable codes so callers
can branch on specific failure types without parsing message strings.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = [
    "ConfigurationError",
    "ConfigurationLoadError",
    "ConfigurationValidationError",
    "ConfigurationNotFoundError",
    "ConfigurationTypeError",
    "ConfigurationRangeError",
    "ConfigurationMergeError",
    "ConfigurationEncryptionError",
    "ConfigurationWatcherError",
    "ConfigurationReloadError",
    "ConfigurationSchemaError",
    "ConfigurationProviderError",
    "FieldValidationError",
    "SectionValidationError",
]


class ConfigurationError(Exception):
    """Base class for all configuration errors.

    Attributes:
        code:    Machine-readable error code (e.g. ``CFG-001``).
        key:     The configuration key or section involved, if applicable.
        context: Additional diagnostic information.
    """

    def __init__(
        self,
        message: str,
        code: str = "CFG-000",
        key: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.key = key
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        parts = [f"[{self.code}] {super().__str__()}"]
        if self.key:
            parts.append(f"(key={self.key!r})")
        return " ".join(parts)


class ConfigurationLoadError(ConfigurationError):
    """Raised when a configuration source cannot be read."""

    def __init__(
        self,
        message: str,
        source: str = "",
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, code="CFG-001", context={"source": source})
        self.source = source
        self.cause = cause

    def __str__(self) -> str:
        base = super().__str__()
        if self.source:
            base += f" [source={self.source!r}]"
        if self.cause:
            base += f" [cause={type(self.cause).__name__}: {self.cause}]"
        return base


class ConfigurationValidationError(ConfigurationError):
    """Raised when loaded configuration fails schema validation."""

    def __init__(
        self,
        message: str,
        key: Optional[str] = None,
        expected: Any = None,
        actual: Any = None,
    ) -> None:
        super().__init__(
            message,
            code="CFG-002",
            key=key,
            context={"expected": expected, "actual": actual},
        )
        self.expected = expected
        self.actual = actual


class ConfigurationNotFoundError(ConfigurationError):
    """Raised when a required configuration key is missing."""

    def __init__(self, key: str, section: Optional[str] = None) -> None:
        loc = f"{section}.{key}" if section else key
        super().__init__(
            f"Required configuration key not found: {loc!r}",
            code="CFG-003",
            key=key,
            context={"section": section},
        )
        self.section = section


class ConfigurationTypeError(ConfigurationError):
    """Raised when a value cannot be coerced to the expected type."""

    def __init__(self, key: str, expected_type: type, actual_value: Any) -> None:
        super().__init__(
            f"Type error for {key!r}: expected {expected_type.__name__}, "
            f"got {type(actual_value).__name__} ({actual_value!r})",
            code="CFG-004",
            key=key,
            context={"expected_type": expected_type.__name__, "actual": actual_value},
        )
        self.expected_type = expected_type
        self.actual_value = actual_value


class ConfigurationRangeError(ConfigurationError):
    """Raised when a numeric value is outside its allowed range."""

    def __init__(
        self,
        key: str,
        value: Any,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
    ) -> None:
        bounds = []
        if min_value is not None:
            bounds.append(f">= {min_value}")
        if max_value is not None:
            bounds.append(f"<= {max_value}")
        super().__init__(
            f"Range error for {key!r}: value {value!r} violates constraint [{', '.join(bounds)}]",
            code="CFG-005",
            key=key,
            context={"value": value, "min": min_value, "max": max_value},
        )
        self.value = value
        self.min_value = min_value
        self.max_value = max_value


class ConfigurationMergeError(ConfigurationError):
    """Raised when configuration sources cannot be merged."""

    def __init__(self, message: str, key: Optional[str] = None) -> None:
        super().__init__(message, code="CFG-006", key=key)


class ConfigurationEncryptionError(ConfigurationError):
    """Raised when encryption or decryption of a secret fails."""

    def __init__(self, message: str, key: Optional[str] = None) -> None:
        super().__init__(message, code="CFG-007", key=key)


class ConfigurationWatcherError(ConfigurationError):
    """Raised when the file-system watcher cannot be started."""

    def __init__(self, message: str, path: str = "") -> None:
        super().__init__(message, code="CFG-008", context={"path": path})
        self.path = path


class ConfigurationReloadError(ConfigurationError):
    """Raised when a hot-reload attempt fails."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message, code="CFG-009")
        self.cause = cause


class ConfigurationSchemaError(ConfigurationError):
    """Raised when a schema definition is malformed."""

    def __init__(self, message: str, schema_name: str = "") -> None:
        super().__init__(message, code="CFG-010", context={"schema": schema_name})
        self.schema_name = schema_name


class ConfigurationProviderError(ConfigurationError):
    """Raised when a configuration provider fails to initialize or read."""

    def __init__(self, message: str, provider: str = "") -> None:
        super().__init__(message, code="CFG-011", context={"provider": provider})
        self.provider = provider


class FieldValidationError(ConfigurationValidationError):
    """Raised for a single field-level validation failure."""

    def __init__(
        self,
        section: str,
        field: str,
        message: str,
        value: Any = None,
    ) -> None:
        super().__init__(
            f"[{section}.{field}] {message}",
            key=f"{section}.{field}",
            actual=value,
        )
        self.section = section
        self.field = field
        self.field_value = value


class SectionValidationError(ConfigurationValidationError):
    """Raised when one or more fields in a section fail validation.

    Aggregates multiple ``FieldValidationError`` instances.
    """

    def __init__(self, section: str, field_errors: list[FieldValidationError]) -> None:
        count = len(field_errors)
        super().__init__(
            f"Section {section!r} has {count} validation error(s):\n"
            + "\n".join(f"  • {e}" for e in field_errors),
            key=section,
        )
        self.section = section
        self.field_errors = field_errors
