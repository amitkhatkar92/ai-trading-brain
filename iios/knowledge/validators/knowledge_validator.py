"""
iios/knowledge/validators/knowledge_validator.py
=================================================
Core validation logic for KnowledgeRecord objects.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from typing import Any, Callable, Optional

from ..knowledge_constants import (
    KnowledgeStatus,
    ValidationResult,
    ConstraintType,
    MIN_CONFIDENCE,
    MAX_CONFIDENCE,
    SCHEMA_VERSION,
)
from ..knowledge_exceptions import (
    KnowledgeValidationError,
    KnowledgeSchemaError,
    KnowledgeConstraintError,
)
from ..models.knowledge_record import KnowledgeRecord

__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "KnowledgeValidator",
    "get_knowledge_validator",
    "reset_knowledge_validator",
]

_LOG = logging.getLogger("iios.knowledge.validator")
_lock = threading.Lock()
_validator: Optional["KnowledgeValidator"] = None


# ── Value objects ─────────────────────────────────────────────────────────────

class ValidationIssue:
    """A single validation finding."""

    __slots__ = ("result", "field", "message", "constraint_type", "code")

    def __init__(
        self,
        result: ValidationResult,
        field: str,
        message: str,
        constraint_type: ConstraintType = ConstraintType.CUSTOM,
        code: str = "",
    ) -> None:
        self.result: ValidationResult = result
        self.field: str = field
        self.message: str = message
        self.constraint_type: ConstraintType = constraint_type
        self.code: str = code

    def is_error(self) -> bool:
        return self.result == ValidationResult.FAIL

    def __repr__(self) -> str:
        return f"ValidationIssue({self.result.value}, {self.field!r}, {self.message!r})"


class ValidationReport:
    """Aggregate result of running a validator against a record."""

    def __init__(self, knowledge_id: str) -> None:
        self.knowledge_id = knowledge_id
        self.issues: list[ValidationIssue] = []

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    def add_error(self, field: str, message: str, code: str = "", ctype: ConstraintType = ConstraintType.CUSTOM) -> None:
        self.issues.append(ValidationIssue(ValidationResult.FAIL, field, message, ctype, code))

    def add_warning(self, field: str, message: str, code: str = "") -> None:
        self.issues.append(ValidationIssue(ValidationResult.WARNING, field, message, code=code))

    @property
    def passed(self) -> bool:
        return not any(i.is_error() for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.is_error()]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.result == ValidationResult.WARNING]

    def raise_if_failed(self) -> None:
        if not self.passed:
            msgs = [f"{e.field}: {e.message}" for e in self.errors]
            raise KnowledgeValidationError(
                f"Validation failed for '{self.knowledge_id}': {'; '.join(msgs)}",
                code="KV-001",
                violations=msgs,
            )

    def __repr__(self) -> str:
        return f"ValidationReport(id={self.knowledge_id!r}, passed={self.passed}, issues={len(self.issues)})"


# ── Validator ─────────────────────────────────────────────────────────────────

RuleFunc = Callable[[KnowledgeRecord, ValidationReport], None]


class KnowledgeValidator:
    """Validates KnowledgeRecord objects against a set of registered rules.

    Built-in rules cover:
    - Identity (knowledge_id, title)
    - Type checks (types, status)
    - Confidence range
    - Content presence
    - Metadata completeness

    Custom rules can be added with ``register_rule()``.

    Usage::

        validator = get_knowledge_validator()
        report = validator.validate(record)
        report.raise_if_failed()
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rules: list[tuple[str, RuleFunc]] = []
        self._register_builtin_rules()

    def _register_builtin_rules(self) -> None:
        self._rules = [
            ("identity",    self._rule_identity),
            ("type",        self._rule_type),
            ("status",      self._rule_status),
            ("confidence",  self._rule_confidence),
            ("content",     self._rule_content),
            ("metadata",    self._rule_metadata),
            ("version",     self._rule_version),
        ]

    # ── Built-in rules ────────────────────────────────────────────────────────

    def _rule_identity(self, rec: KnowledgeRecord, report: ValidationReport) -> None:
        if not rec.knowledge_id or not rec.knowledge_id.uid:
            report.add_error("knowledge_id", "knowledge_id.uid must not be empty",
                             code="KV-ID-001", ctype=ConstraintType.REQUIRED)
        if not rec.title or not rec.title.strip():
            report.add_warning("title", "title is empty — consider adding a descriptive title")

    def _rule_type(self, rec: KnowledgeRecord, report: ValidationReport) -> None:
        from ..knowledge_constants import KnowledgeType
        try:
            KnowledgeType(rec.knowledge_type)
        except ValueError:
            report.add_error("knowledge_type", f"Unknown knowledge_type '{rec.knowledge_type}'",
                             code="KV-TYPE-001", ctype=ConstraintType.TYPE)

    def _rule_status(self, rec: KnowledgeRecord, report: ValidationReport) -> None:
        try:
            KnowledgeStatus(rec.status)
        except ValueError:
            report.add_error("status", f"Unknown status '{rec.status}'",
                             code="KV-STATUS-001", ctype=ConstraintType.TYPE)

    def _rule_confidence(self, rec: KnowledgeRecord, report: ValidationReport) -> None:
        c = rec.metadata.confidence
        if not (MIN_CONFIDENCE <= c <= MAX_CONFIDENCE):
            report.add_error("metadata.confidence",
                             f"Confidence {c} out of range [{MIN_CONFIDENCE}, {MAX_CONFIDENCE}]",
                             code="KV-CONF-001", ctype=ConstraintType.RANGE)

    def _rule_content(self, rec: KnowledgeRecord, report: ValidationReport) -> None:
        if rec.content is None:
            report.add_warning("content", "content is None — may be intentional for placeholder records")

    def _rule_metadata(self, rec: KnowledgeRecord, report: ValidationReport) -> None:
        if not rec.metadata.owner_id:
            report.add_error("metadata.owner_id", "owner_id must not be empty",
                             code="KV-META-001", ctype=ConstraintType.REQUIRED)

    def _rule_version(self, rec: KnowledgeRecord, report: ValidationReport) -> None:
        parts = rec.version.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            report.add_error("version", f"version '{rec.version}' must be semver (MAJOR.MINOR.PATCH)",
                             code="KV-VER-001", ctype=ConstraintType.PATTERN)
        if rec.version_sequence < 1:
            report.add_error("version_sequence", "version_sequence must be ≥ 1",
                             code="KV-VER-002", ctype=ConstraintType.RANGE)

    # ── Public API ────────────────────────────────────────────────────────────

    def register_rule(self, name: str, fn: RuleFunc) -> None:
        """Add a custom validation rule."""
        with self._lock:
            # Replace if name already exists
            self._rules = [(n, f) for (n, f) in self._rules if n != name]
            self._rules.append((name, fn))

    def unregister_rule(self, name: str) -> bool:
        with self._lock:
            before = len(self._rules)
            self._rules = [(n, f) for (n, f) in self._rules if n != name]
            return len(self._rules) < before

    def validate(self, record: KnowledgeRecord) -> ValidationReport:
        """Run all registered rules. Returns a ValidationReport."""
        report = ValidationReport(record.id)
        with self._lock:
            rules = list(self._rules)
        for name, fn in rules:
            try:
                fn(record, report)
            except Exception as exc:
                _LOG.warning("Rule '%s' raised an exception: %s", name, exc)
                report.add_error(name, f"Rule error: {exc}", code="KV-RULE-ERR")
        return report

    def validate_or_raise(self, record: KnowledgeRecord) -> ValidationReport:
        """Validate and raise KnowledgeValidationError on failure."""
        report = self.validate(record)
        report.raise_if_failed()
        return report

    def compute_checksum(self, record: KnowledgeRecord) -> str:
        """Compute a SHA-256 checksum of the record content."""
        try:
            payload = json.dumps(record.content, sort_keys=True, default=str)
        except (TypeError, ValueError):
            payload = str(record.content)
        return hashlib.sha256(payload.encode()).hexdigest()

    def list_rules(self) -> list[str]:
        with self._lock:
            return [n for (n, _) in self._rules]


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_knowledge_validator() -> KnowledgeValidator:
    global _validator
    with _lock:
        if _validator is None:
            _validator = KnowledgeValidator()
        return _validator


def reset_knowledge_validator() -> None:
    global _validator
    with _lock:
        _validator = None
