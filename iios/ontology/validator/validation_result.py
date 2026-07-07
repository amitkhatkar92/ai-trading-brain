"""
iios/ontology/validator/validation_result.py
=============================================
Atomic validation result for a single constraint check.

Each check produces a ValidationResult that is then collected into a
ValidationReport.  Results are immutable once created.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .validation_constants import ValidationScope, ValidationSeverity

__all__ = [
    "ValidationResult",
]


@dataclass
class ValidationResult:
    """
    Outcome of evaluating a single constraint or validation rule.

    Attributes:
        passed        – True when the check found no violation.
        severity      – Severity of the finding (PASS if passed=True).
        scope         – The structural unit that was checked.
        constraint_id – Stable identifier of the rule that produced this result.
        message       – Human-readable description of the finding.
        path          – Dot-separated path inside the target (e.g. "properties.price.ref_uri").
        details       – Optional structured data for programmatic consumers.
        fix_suggestion– Optional hint on how to resolve the violation.
        timestamp     – Unix epoch seconds when the result was produced.
        target_uri    – URI of the object being validated (if known).
    """

    passed:         bool                   = True
    severity:       ValidationSeverity     = ValidationSeverity.PASS
    scope:          ValidationScope        = ValidationScope.TYPE
    constraint_id:  str                    = ""
    message:        str                    = ""
    path:           str                    = ""
    details:        dict[str, Any]         = field(default_factory=dict)
    fix_suggestion: str                    = ""
    timestamp:      float                  = field(default_factory=time.time)
    target_uri:     str                    = ""

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def ok(
        cls,
        constraint_id: str,
        scope:         ValidationScope = ValidationScope.TYPE,
        message:       str             = "",
        target_uri:    str             = "",
        path:          str             = "",
    ) -> "ValidationResult":
        """Produce a PASS result."""
        return cls(
            passed        = True,
            severity      = ValidationSeverity.PASS,
            scope         = scope,
            constraint_id = constraint_id,
            message       = message or f"{constraint_id} passed",
            target_uri    = target_uri,
            path          = path,
        )

    @classmethod
    def fail(
        cls,
        constraint_id:  str,
        message:        str,
        scope:          ValidationScope    = ValidationScope.TYPE,
        severity:       ValidationSeverity = ValidationSeverity.ERROR,
        path:           str                = "",
        details:        Optional[dict[str, Any]] = None,
        fix_suggestion: str                = "",
        target_uri:     str                = "",
    ) -> "ValidationResult":
        """Produce a failure result (ERROR by default)."""
        return cls(
            passed        = False,
            severity      = severity,
            scope         = scope,
            constraint_id = constraint_id,
            message       = message,
            path          = path,
            details       = details or {},
            fix_suggestion= fix_suggestion,
            target_uri    = target_uri,
        )

    @classmethod
    def warn(
        cls,
        constraint_id:  str,
        message:        str,
        scope:          ValidationScope = ValidationScope.TYPE,
        path:           str             = "",
        details:        Optional[dict[str, Any]] = None,
        fix_suggestion: str             = "",
        target_uri:     str             = "",
    ) -> "ValidationResult":
        """Produce a WARNING result (does not count as failure)."""
        return cls(
            passed        = True,   # warnings don't block
            severity      = ValidationSeverity.WARNING,
            scope         = scope,
            constraint_id = constraint_id,
            message       = message,
            path          = path,
            details       = details or {},
            fix_suggestion= fix_suggestion,
            target_uri    = target_uri,
        )

    @classmethod
    def info(
        cls,
        constraint_id: str,
        message:       str,
        scope:         ValidationScope = ValidationScope.TYPE,
        target_uri:    str             = "",
    ) -> "ValidationResult":
        """Produce an INFO result (purely informational)."""
        return cls(
            passed        = True,
            severity      = ValidationSeverity.INFO,
            scope         = scope,
            constraint_id = constraint_id,
            message       = message,
            target_uri    = target_uri,
        )

    @classmethod
    def critical(
        cls,
        constraint_id:  str,
        message:        str,
        scope:          ValidationScope = ValidationScope.TYPE,
        path:           str             = "",
        details:        Optional[dict[str, Any]] = None,
        fix_suggestion: str             = "",
        target_uri:     str             = "",
    ) -> "ValidationResult":
        """Produce a CRITICAL result — always blocks operations."""
        return cls(
            passed        = False,
            severity      = ValidationSeverity.CRITICAL,
            scope         = scope,
            constraint_id = constraint_id,
            message       = message,
            path          = path,
            details       = details or {},
            fix_suggestion= fix_suggestion,
            target_uri    = target_uri,
        )

    # ── Convenience properties ─────────────────────────────────────────────────

    @property
    def is_error(self) -> bool:
        return self.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)

    @property
    def is_warning(self) -> bool:
        return self.severity == ValidationSeverity.WARNING

    @property
    def is_critical(self) -> bool:
        return self.severity == ValidationSeverity.CRITICAL

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":         self.passed,
            "severity":       self.severity.value,
            "scope":          self.scope.value,
            "constraint_id":  self.constraint_id,
            "message":        self.message,
            "path":           self.path,
            "details":        self.details,
            "fix_suggestion": self.fix_suggestion,
            "timestamp":      self.timestamp,
            "target_uri":     self.target_uri,
        }
