"""
iios/ontology/validator/constraint_registry.py
===============================================
Registry for constraint definitions.

Each constraint is a callable rule that accepts a target object plus
a shared ``all_types`` dict and returns a list[ValidationResult].
The registry allows per-constraint enable/disable without removing
the definition.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .validation_constants import (
    ConstraintType,
    ValidationScope,
    ValidationSeverity,
)
from .validation_exceptions import DuplicateConstraintError, UnknownConstraintError
from .validation_result import ValidationResult

__all__ = [
    "ConstraintDef",
    "ConstraintRegistry",
    "get_constraint_registry",
    "reset_constraint_registry",
]

# Callable type alias: rule(target, all_types) → list[ValidationResult]
ConstraintRule = Callable[[Any, dict[str, Any]], list[ValidationResult]]


@dataclass
class ConstraintDef:
    """
    Metadata and callable for one constraint rule.

    Attributes:
        constraint_id   – Stable dot-separated identifier, e.g. "builtin.type.has_uri"
        name            – Short human label
        constraint_type – Category (ConstraintType enum)
        scope           – Which structural unit this applies to (ValidationScope)
        severity        – Default severity when the rule fires
        enabled         – Whether the rule runs at all
        description     – Prose description of what the rule enforces
        rule            – The callable ``rule(target, all_types) → list[ValidationResult]``
        tags            – Optional labels for grouping
    """

    constraint_id:   str
    name:            str
    constraint_type: ConstraintType
    scope:           ValidationScope
    severity:        ValidationSeverity
    rule:            ConstraintRule
    enabled:         bool          = True
    description:     str           = ""
    tags:            list[str]     = field(default_factory=list)

    def __call__(self, target: Any, all_types: dict[str, Any]) -> list[ValidationResult]:
        """Invoke the underlying rule (only when enabled)."""
        if not self.enabled:
            return []
        return self.rule(target, all_types)


class ConstraintRegistry:
    """
    Thread-safe store for ConstraintDef objects.

    Supports:
      - Registration with duplicate detection
      - Lookup by ID, scope, or constraint type
      - Enable / disable individual constraints
      - Bulk-enable / bulk-disable by scope or type
    """

    def __init__(self) -> None:
        self._lock:        threading.RLock            = threading.RLock()
        self._constraints: dict[str, ConstraintDef]  = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        constraint_id:   str,
        name:            str,
        constraint_type: ConstraintType,
        scope:           ValidationScope,
        severity:        ValidationSeverity,
        rule:            ConstraintRule,
        description:     str          = "",
        tags:            Optional[list[str]] = None,
        overwrite:       bool         = False,
    ) -> ConstraintDef:
        """
        Register a new constraint.

        Args:
            overwrite: If True, replace an existing constraint with the same ID.

        Raises:
            DuplicateConstraintError: If the ID exists and overwrite=False.
        """
        with self._lock:
            if constraint_id in self._constraints and not overwrite:
                raise DuplicateConstraintError(constraint_id)
            cd = ConstraintDef(
                constraint_id   = constraint_id,
                name            = name,
                constraint_type = constraint_type,
                scope           = scope,
                severity        = severity,
                rule            = rule,
                description     = description,
                tags            = list(tags or []),
            )
            self._constraints[constraint_id] = cd
            return cd

    def unregister(self, constraint_id: str) -> None:
        """Remove a constraint by ID.

        Raises:
            UnknownConstraintError: If the ID does not exist.
        """
        with self._lock:
            if constraint_id not in self._constraints:
                raise UnknownConstraintError(constraint_id)
            del self._constraints[constraint_id]

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, constraint_id: str) -> ConstraintDef:
        with self._lock:
            if constraint_id not in self._constraints:
                raise UnknownConstraintError(constraint_id)
            return self._constraints[constraint_id]

    def has(self, constraint_id: str) -> bool:
        with self._lock:
            return constraint_id in self._constraints

    def get_by_scope(self, scope: ValidationScope, enabled_only: bool = True) -> list[ConstraintDef]:
        with self._lock:
            return [
                cd for cd in self._constraints.values()
                if cd.scope == scope and (not enabled_only or cd.enabled)
            ]

    def get_by_type(self, constraint_type: ConstraintType, enabled_only: bool = True) -> list[ConstraintDef]:
        with self._lock:
            return [
                cd for cd in self._constraints.values()
                if cd.constraint_type == constraint_type and (not enabled_only or cd.enabled)
            ]

    def get_by_tag(self, tag: str, enabled_only: bool = True) -> list[ConstraintDef]:
        with self._lock:
            return [
                cd for cd in self._constraints.values()
                if tag in cd.tags and (not enabled_only or cd.enabled)
            ]

    def all_ids(self) -> list[str]:
        with self._lock:
            return list(self._constraints.keys())

    def all_enabled(self) -> list[ConstraintDef]:
        with self._lock:
            return [cd for cd in self._constraints.values() if cd.enabled]

    # ── Enable / disable ──────────────────────────────────────────────────────

    def enable(self, constraint_id: str) -> None:
        with self._lock:
            if constraint_id not in self._constraints:
                raise UnknownConstraintError(constraint_id)
            self._constraints[constraint_id].enabled = True

    def disable(self, constraint_id: str) -> None:
        with self._lock:
            if constraint_id not in self._constraints:
                raise UnknownConstraintError(constraint_id)
            self._constraints[constraint_id].enabled = False

    def enable_by_scope(self, scope: ValidationScope) -> int:
        with self._lock:
            count = 0
            for cd in self._constraints.values():
                if cd.scope == scope:
                    cd.enabled = True
                    count += 1
            return count

    def disable_by_scope(self, scope: ValidationScope) -> int:
        with self._lock:
            count = 0
            for cd in self._constraints.values():
                if cd.scope == scope:
                    cd.enabled = False
                    count += 1
            return count

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total   = len(self._constraints)
            enabled = sum(1 for cd in self._constraints.values() if cd.enabled)
            by_scope: dict[str, int] = {}
            by_type:  dict[str, int] = {}
            for cd in self._constraints.values():
                by_scope[cd.scope.value]           = by_scope.get(cd.scope.value, 0) + 1
                by_type[cd.constraint_type.value]  = by_type.get(cd.constraint_type.value, 0) + 1
            return {
                "total":    total,
                "enabled":  enabled,
                "disabled": total - enabled,
                "by_scope": by_scope,
                "by_type":  by_type,
            }

    def clear(self) -> None:
        with self._lock:
            self._constraints.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

_lock:     threading.Lock               = threading.Lock()
_registry: Optional[ConstraintRegistry] = None


def get_constraint_registry() -> ConstraintRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = ConstraintRegistry()
    return _registry


def reset_constraint_registry() -> None:
    global _registry
    with _lock:
        _registry = None
