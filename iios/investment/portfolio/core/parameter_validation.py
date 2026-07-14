"""iios/investment/portfolio/core/parameter_validation.py

Parameter-level validation rules for the Institutional Portfolio Framework.
Separated from configuration to allow rule composition and extensibility.
"""
from __future__ import annotations

import math
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.investment.portfolio.core.portfolio_types import ValidationOutcome
from iios.investment.portfolio.core.parameter_registry import ParameterDefinition, ParameterType


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a single validation rule applied to one field."""

    result_id:   str              = field(default_factory=lambda: str(uuid.uuid4()))
    field_name:  str              = ""
    rule_name:   str              = ""
    outcome:     ValidationOutcome= ValidationOutcome.PASSED
    message:     str              = ""
    actual:      Any              = None
    expected:    str              = ""
    checked_at:  float            = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return self.outcome == ValidationOutcome.PASSED

    @property
    def is_blocking(self) -> bool:
        return self.outcome.is_blocking

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":  self.result_id,
            "field_name": self.field_name,
            "rule_name":  self.rule_name,
            "outcome":    self.outcome.value,
            "message":    self.message,
            "actual":     self.actual,
            "expected":   self.expected,
        }


def _pass(field_name: str, rule_name: str) -> ValidationResult:
    return ValidationResult(
        field_name=field_name, rule_name=rule_name,
        outcome=ValidationOutcome.PASSED, message="OK",
    )


def _fail(field_name: str, rule_name: str, message: str,
          actual: Any = None, expected: str = "") -> ValidationResult:
    return ValidationResult(
        field_name=field_name, rule_name=rule_name,
        outcome=ValidationOutcome.FAILED, message=message,
        actual=actual, expected=expected,
    )


def _warn(field_name: str, rule_name: str, message: str) -> ValidationResult:
    return ValidationResult(
        field_name=field_name, rule_name=rule_name,
        outcome=ValidationOutcome.WARNING, message=message,
    )


# ---------------------------------------------------------------------------
# Rule base class
# ---------------------------------------------------------------------------

class ValidationRule(ABC):
    """Abstract base for parameter validation rules."""

    @property
    @abstractmethod
    def rule_name(self) -> str: ...

    @abstractmethod
    def validate(self, field_name: str, value: Any) -> ValidationResult: ...


# ---------------------------------------------------------------------------
# Concrete rules
# ---------------------------------------------------------------------------

class RequiredRule(ValidationRule):
    """Fails if value is None."""

    @property
    def rule_name(self) -> str:
        return "required"

    def validate(self, field_name: str, value: Any) -> ValidationResult:
        if value is None:
            return _fail(field_name, self.rule_name, f"{field_name!r} is required")
        return _pass(field_name, self.rule_name)


class MinValueRule(ValidationRule):
    """Numeric lower bound check."""

    def __init__(self, min_val: float, *, inclusive: bool = True) -> None:
        self._min       = min_val
        self._inclusive = inclusive

    @property
    def rule_name(self) -> str:
        return f"min_value({self._min})"

    def validate(self, field_name: str, value: Any) -> ValidationResult:
        if value is None:
            return _pass(field_name, self.rule_name)
        try:
            v = float(value)
        except (TypeError, ValueError):
            return _fail(field_name, self.rule_name, f"{field_name!r} must be numeric")
        ok = v >= self._min if self._inclusive else v > self._min
        if not ok:
            op = ">=" if self._inclusive else ">"
            return _fail(field_name, self.rule_name,
                         f"{field_name!r} = {v} must be {op} {self._min}",
                         actual=v, expected=f"{op} {self._min}")
        return _pass(field_name, self.rule_name)


class MaxValueRule(ValidationRule):
    """Numeric upper bound check."""

    def __init__(self, max_val: float, *, inclusive: bool = True) -> None:
        self._max       = max_val
        self._inclusive = inclusive

    @property
    def rule_name(self) -> str:
        return f"max_value({self._max})"

    def validate(self, field_name: str, value: Any) -> ValidationResult:
        if value is None:
            return _pass(field_name, self.rule_name)
        try:
            v = float(value)
        except (TypeError, ValueError):
            return _fail(field_name, self.rule_name, f"{field_name!r} must be numeric")
        ok = v <= self._max if self._inclusive else v < self._max
        if not ok:
            op = "<=" if self._inclusive else "<"
            return _fail(field_name, self.rule_name,
                         f"{field_name!r} = {v} must be {op} {self._max}",
                         actual=v, expected=f"{op} {self._max}")
        return _pass(field_name, self.rule_name)


class RangeRule(ValidationRule):
    """Numeric range [min, max] check."""

    def __init__(self, min_val: float, max_val: float) -> None:
        self._min = min_val
        self._max = max_val

    @property
    def rule_name(self) -> str:
        return f"range([{self._min}, {self._max}])"

    def validate(self, field_name: str, value: Any) -> ValidationResult:
        if value is None:
            return _pass(field_name, self.rule_name)
        try:
            v = float(value)
        except (TypeError, ValueError):
            return _fail(field_name, self.rule_name, f"{field_name!r} must be numeric")
        if not (self._min <= v <= self._max):
            return _fail(field_name, self.rule_name,
                         f"{field_name!r} = {v} out of range [{self._min}, {self._max}]",
                         actual=v, expected=f"[{self._min}, {self._max}]")
        return _pass(field_name, self.rule_name)


class AllowedValuesRule(ValidationRule):
    """Enumeration membership check."""

    def __init__(self, allowed: set[str]) -> None:
        self._allowed = frozenset(allowed)

    @property
    def rule_name(self) -> str:
        return "allowed_values"

    def validate(self, field_name: str, value: Any) -> ValidationResult:
        if value is None:
            return _pass(field_name, self.rule_name)
        if str(value) not in self._allowed:
            return _fail(field_name, self.rule_name,
                         f"{field_name!r} = {value!r} not in allowed set",
                         actual=value,
                         expected=f"one of {sorted(self._allowed)}")
        return _pass(field_name, self.rule_name)


class FiniteFloatRule(ValidationRule):
    """Rejects NaN and Inf."""

    @property
    def rule_name(self) -> str:
        return "finite_float"

    def validate(self, field_name: str, value: Any) -> ValidationResult:
        if value is None:
            return _pass(field_name, self.rule_name)
        try:
            v = float(value)
        except (TypeError, ValueError):
            return _pass(field_name, self.rule_name)  # type mismatch handled elsewhere
        if not math.isfinite(v):
            return _fail(field_name, self.rule_name,
                         f"{field_name!r} must be a finite number, got {v!r}",
                         actual=value)
        return _pass(field_name, self.rule_name)


class PositiveRule(ValidationRule):
    """Value must be strictly positive."""

    @property
    def rule_name(self) -> str:
        return "positive"

    def validate(self, field_name: str, value: Any) -> ValidationResult:
        if value is None:
            return _pass(field_name, self.rule_name)
        try:
            if float(value) <= 0:
                return _fail(field_name, self.rule_name,
                             f"{field_name!r} must be > 0", actual=value, expected="> 0")
        except (TypeError, ValueError):
            pass
        return _pass(field_name, self.rule_name)


# ---------------------------------------------------------------------------
# ParameterValidator — applies ParameterDefinition rules
# ---------------------------------------------------------------------------

class ParameterValidator:
    """
    Validates a value against a ParameterDefinition.
    Returns all ValidationResult objects (pass and fail).
    """

    @staticmethod
    def validate(defn: ParameterDefinition, value: Any) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        fn = defn.name

        # Required check
        if defn.required:
            results.append(RequiredRule().validate(fn, value))
            if value is None:
                return results  # nothing more to check

        if value is None:
            return results  # optional and absent — all OK

        # Finite float
        if defn.param_type in (ParameterType.FLOAT, ParameterType.INTEGER):
            results.append(FiniteFloatRule().validate(fn, value))

        # Range
        if defn.min_value is not None:
            results.append(MinValueRule(defn.min_value).validate(fn, value))
        if defn.max_value is not None:
            results.append(MaxValueRule(defn.max_value).validate(fn, value))

        # Allowed values (enum)
        if defn.allowed_values:
            results.append(AllowedValuesRule(set(defn.allowed_values)).validate(fn, value))

        # Custom validator
        if defn.validator is not None:
            try:
                defn.validator(value)
            except ValueError as exc:
                results.append(_fail(fn, "custom_validator", str(exc), actual=value))

        return results

    @staticmethod
    def validate_all(defn: ParameterDefinition, value: Any) -> list[ValidationResult]:
        """Alias of validate for clarity."""
        return ParameterValidator.validate(defn, value)

    @staticmethod
    def is_valid(defn: ParameterDefinition, value: Any) -> bool:
        return all(r.passed for r in ParameterValidator.validate(defn, value))
