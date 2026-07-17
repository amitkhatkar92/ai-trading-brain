"""iios/execution/risk/rules/rule_validation.py
==================================================
RuleFrameworkValidator — structural validation of rules and their
registration into the framework.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import RuleValidationError


@dataclass(frozen=True)
class ValidationResult:
    """Result of a framework validation pass."""

    is_valid:     bool
    errors:       Tuple[str, ...]
    warnings:     Tuple[str, ...]
    validated_at: float = field(default_factory=time.time)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":      self.is_valid,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "error_count":   self.error_count,
            "warning_count": self.warning_count,
        }


def _ok(warnings: List[str] | None = None) -> ValidationResult:
    return ValidationResult(is_valid=True, errors=(), warnings=tuple(warnings or []))


def _fail(errors: List[str], warnings: List[str] | None = None) -> ValidationResult:
    return ValidationResult(is_valid=False, errors=tuple(errors), warnings=tuple(warnings or []))


class RuleFrameworkValidator:
    """
    Stateless validator for rule structural integrity and registry consistency.
    """

    # ── Rule structural validation ────────────────────────────────────────────

    def validate_rule(self, rule: Any) -> ValidationResult:
        """Validate a rule's required properties before registration."""
        errors:   List[str] = []
        warnings: List[str] = []

        # rule_id
        try:
            rid = rule.rule_id
            if not rid or not isinstance(rid, str):
                errors.append("rule_id must be a non-empty string")
        except Exception as exc:
            errors.append(f"rule_id accessor raised: {exc}")
            rid = ""

        # rule_name
        try:
            rname = rule.rule_name
            if not rname or not isinstance(rname, str):
                errors.append("rule_name must be a non-empty string")
        except Exception as exc:
            errors.append(f"rule_name accessor raised: {exc}")

        # category()
        try:
            cat = rule.category()
            if cat is None:
                errors.append("category() must return a non-None RuleCategory")
        except Exception as exc:
            errors.append(f"category() raised: {exc}")

        # priority()
        try:
            p = rule.priority()
            if not isinstance(p, (int, float)):
                errors.append("priority() must return an int or float")
            elif p < 0:
                errors.append("priority() must be >= 0")
        except Exception as exc:
            errors.append(f"priority() raised: {exc}")

        # enabled()
        try:
            _ = rule.enabled()
        except Exception as exc:
            errors.append(f"enabled() raised: {exc}")

        # evaluate callable
        if not callable(getattr(rule, "evaluate", None)):
            errors.append("rule must have a callable evaluate() method")

        # _evaluate callable
        if not callable(getattr(rule, "_evaluate", None)):
            warnings.append("rule should implement _evaluate() as per framework convention")

        if errors:
            return _fail(errors, warnings)
        return _ok(warnings)

    # ── Registry consistency validation ──────────────────────────────────────

    def validate_unique_id(self, rule: Any, existing_ids: List[str]) -> ValidationResult:
        """Validate that rule_id is not already in the registry."""
        try:
            rid = rule.rule_id
        except Exception:
            return _fail(["Cannot read rule_id"])

        if rid in existing_ids:
            return _fail([f"Duplicate rule_id '{rid}' — already registered"])
        return _ok()

    def validate_priority_conflict(
        self, rule: Any, existing_rules: List[Any]
    ) -> ValidationResult:
        """Warn on priority conflicts (same priority value in same category)."""
        warnings: List[str] = []
        try:
            prio = int(rule.priority())
            cat  = rule.category().value
        except Exception:
            return _ok()

        for existing in existing_rules:
            try:
                if int(existing.priority()) == prio and existing.category().value == cat:
                    warnings.append(
                        f"Priority conflict: rule '{rule.rule_id}' and '{existing.rule_id}' "
                        f"both have priority {prio} in category {cat}"
                    )
            except Exception:
                continue

        return _ok(warnings)

    def validate_no_circular_deps(
        self, rule: Any, existing_rules: List[Any]
    ) -> ValidationResult:
        """
        Check for circular dependency chains.

        BaseRule does not currently support explicit dependency declarations;
        this check validates that a rule does not list itself as a dependency
        via optional ``depends_on`` attribute.
        """
        deps = getattr(rule, "depends_on", None)
        if not deps:
            return _ok()

        try:
            dep_ids = set(deps)
        except Exception:
            return _fail(["depends_on must be iterable"])

        try:
            if rule.rule_id in dep_ids:
                return _fail([f"Rule '{rule.rule_id}' declares itself as a dependency"])
        except Exception:
            pass

        return _ok()

    def validate_result_consistency(self, result: Any) -> ValidationResult:
        """Validate that a RuleResult is internally consistent."""
        errors: List[str] = []

        if not hasattr(result, "outcome"):
            errors.append("result must have an outcome field")

        if not hasattr(result, "rule_id") or not result.rule_id:
            errors.append("result must have a non-empty rule_id")

        if not hasattr(result, "elapsed_ms") or result.elapsed_ms < 0:
            errors.append("result.elapsed_ms must be >= 0")

        if errors:
            return _fail(errors)
        return _ok()

    # ── Convenience ───────────────────────────────────────────────────────────

    def raise_if_invalid(self, result: ValidationResult, context: str = "") -> None:
        if not result.is_valid:
            detail = "; ".join(result.errors)
            msg    = f"{context}: {detail}" if context else detail
            raise RuleValidationError(msg)
