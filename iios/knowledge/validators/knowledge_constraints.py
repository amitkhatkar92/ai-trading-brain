"""
iios/knowledge/validators/knowledge_constraints.py
====================================================
Constraint definitions and checker for structural rules on knowledge items.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..knowledge_constants import ConstraintType, ValidationResult, KnowledgeType
from ..knowledge_exceptions import KnowledgeConstraintError
from ..models.knowledge_record import KnowledgeRecord
from .knowledge_validator import ValidationIssue, ValidationReport

__all__ = [
    "ConstraintDefinition",
    "ConstraintChecker",
    "get_constraint_checker",
    "reset_constraint_checker",
]

_lock = threading.Lock()
_checker: Optional["ConstraintChecker"] = None


@dataclass
class ConstraintDefinition:
    """Describes a single constraint on a field of a knowledge record."""
    name:             str
    constraint_type:  ConstraintType
    target_field:     str
    check_fn:         Callable[[Any], bool]
    message_template: str  = ""
    applies_to_types: list[KnowledgeType] = field(default_factory=list)
    is_hard:          bool = True   # True = error, False = warning
    code:             str  = ""


class ConstraintChecker:
    """Runs registered ConstraintDefinitions against knowledge records.

    Complements KnowledgeValidator with domain-specific hard constraints.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._constraints: dict[str, ConstraintDefinition] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        # Confidence must be between 0 and 1
        self.register(ConstraintDefinition(
            name="confidence_range",
            constraint_type=ConstraintType.RANGE,
            target_field="metadata.confidence",
            check_fn=lambda v: isinstance(v, (int, float)) and 0.0 <= v <= 1.0,
            message_template="confidence must be in [0.0, 1.0]",
            is_hard=True,
            code="KCC-001",
        ))
        # Title must be a string
        self.register(ConstraintDefinition(
            name="title_type",
            constraint_type=ConstraintType.TYPE,
            target_field="title",
            check_fn=lambda v: isinstance(v, str),
            message_template="title must be a string",
            is_hard=True,
            code="KCC-002",
        ))
        # Version must be non-empty string
        self.register(ConstraintDefinition(
            name="version_nonempty",
            constraint_type=ConstraintType.REQUIRED,
            target_field="version",
            check_fn=lambda v: isinstance(v, str) and len(v) > 0,
            message_template="version must be a non-empty string",
            is_hard=True,
            code="KCC-003",
        ))

    def register(self, constraint: ConstraintDefinition) -> None:
        with self._lock:
            self._constraints[constraint.name] = constraint

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._constraints.pop(name, None) is not None

    def _resolve_field(self, record: KnowledgeRecord, field_path: str) -> Any:
        """Resolve a dot-separated field path from a KnowledgeRecord."""
        obj: Any = record
        for part in field_path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)
            if obj is None:
                return None
        return obj

    def check(self, record: KnowledgeRecord) -> list[ValidationIssue]:
        """Run all constraints. Returns list of issues (empty = all pass)."""
        issues: list[ValidationIssue] = []
        with self._lock:
            constraints = list(self._constraints.values())
        for c in constraints:
            # Type filter
            if c.applies_to_types and record.knowledge_type not in c.applies_to_types:
                continue
            value = self._resolve_field(record, c.target_field)
            try:
                ok = c.check_fn(value)
            except Exception as exc:
                ok = False
                c.message_template = f"Error evaluating constraint: {exc}"
            if not ok:
                result = ValidationResult.FAIL if c.is_hard else ValidationResult.WARNING
                issues.append(ValidationIssue(
                    result=result,
                    field=c.target_field,
                    message=c.message_template,
                    constraint_type=c.constraint_type,
                    code=c.code,
                ))
        return issues

    def check_or_raise(self, record: KnowledgeRecord) -> None:
        issues = self.check(record)
        errors = [i for i in issues if i.is_error()]
        if errors:
            msgs = [f"{e.field}: {e.message}" for e in errors]
            raise KnowledgeConstraintError(
                f"Constraint violation(s): {'; '.join(msgs)}",
                code="KCC-100",
                violations=msgs,
            )

    def list_names(self) -> list[str]:
        with self._lock:
            return list(self._constraints.keys())


def get_constraint_checker() -> ConstraintChecker:
    global _checker
    with _lock:
        if _checker is None:
            _checker = ConstraintChecker()
        return _checker


def reset_constraint_checker() -> None:
    global _checker
    with _lock:
        _checker = None
