"""iios/decision_policies/constraints/constraint.py — Abstract Constraint base + concrete implementations."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Callable

from ..policy_constants import ConstraintType
from ..policy_context import EvaluationContext
from .constraint_result import ConstraintResult


# ── Abstract base ─────────────────────────────────────────────────────────────

class Constraint(ABC):
    @property
    @abstractmethod
    def constraint_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.CUSTOM

    @property
    def mandatory(self) -> bool:
        """True → hard (blocking); False → soft (warning only)."""
        return True

    def is_applicable(self, context: EvaluationContext) -> bool:
        return True

    @abstractmethod
    def validate(self, context: EvaluationContext) -> ConstraintResult: ...

    def to_dict(self) -> dict:
        return {
            "constraint_id":   self.constraint_id,
            "name":            self.name,
            "constraint_type": self.constraint_type.value,
            "mandatory":       self.mandatory,
        }


class HardConstraint(Constraint, ABC):
    """Blocking constraint — decision is rejected on violation."""
    @property
    def mandatory(self) -> bool:
        return True


class SoftConstraint(Constraint, ABC):
    """Non-blocking constraint — violation produces warning only."""
    @property
    def mandatory(self) -> bool:
        return False


# ── StaticConstraint ──────────────────────────────────────────────────────────

class StaticConstraint(Constraint):
    """Constraint backed by a fixed validator callable."""

    def __init__(
        self,
        constraint_id:   str,
        name:            str,
        validator:       Callable[[EvaluationContext], tuple[bool, str]],
        *,
        constraint_type: ConstraintType = ConstraintType.CUSTOM,
        mandatory:       bool = True,
        condition:       Callable[[EvaluationContext], bool] | None = None,
    ) -> None:
        self._id        = constraint_id
        self._name      = name
        self._validator = validator
        self._type      = constraint_type
        self._mandatory = mandatory
        self._condition = condition

    @property
    def constraint_id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def constraint_type(self) -> ConstraintType:
        return self._type

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    def is_applicable(self, context: EvaluationContext) -> bool:
        if self._condition is not None:
            return bool(self._condition(context))
        return True

    def validate(self, context: EvaluationContext) -> ConstraintResult:
        t0 = time.perf_counter()
        if not self.is_applicable(context):
            return ConstraintResult(
                constraint_id   = self._id,
                constraint_name = self._name,
                constraint_type = self._type,
                passed          = True,
                is_hard         = self._mandatory,
                reason          = "not applicable (skipped)",
                severity        = "INFO",
                duration_ms     = (time.perf_counter() - t0) * 1_000,
            )
        try:
            passed, reason = self._validator(context)
        except Exception as exc:  # noqa: BLE001
            return ConstraintResult(
                constraint_id   = self._id,
                constraint_name = self._name,
                constraint_type = self._type,
                passed          = False,
                is_hard         = self._mandatory,
                reason          = f"validation error: {exc}",
                severity        = "ERROR",
                duration_ms     = (time.perf_counter() - t0) * 1_000,
            )
        severity = "INFO" if passed else ("ERROR" if self._mandatory else "WARNING")
        return ConstraintResult(
            constraint_id   = self._id,
            constraint_name = self._name,
            constraint_type = self._type,
            passed          = passed,
            is_hard         = self._mandatory,
            reason          = reason,
            severity        = severity,
            duration_ms     = (time.perf_counter() - t0) * 1_000,
        )


# ── BoundedConstraint ─────────────────────────────────────────────────────────

class BoundedConstraint(StaticConstraint):
    """Validates that a numeric payload value falls within [min_val, max_val]."""

    def __init__(
        self,
        constraint_id:   str,
        name:            str,
        key:             str,
        min_val:         float | None = None,
        max_val:         float | None = None,
        *,
        constraint_type: ConstraintType = ConstraintType.CUSTOM,
        mandatory:       bool = True,
    ) -> None:
        self._key     = key
        self._min_val = min_val
        self._max_val = max_val
        super().__init__(
            constraint_id   = constraint_id,
            name            = name,
            validator       = self._bounded_check,
            constraint_type = constraint_type,
            mandatory       = mandatory,
        )

    def _bounded_check(self, ctx: EvaluationContext) -> tuple[bool, str]:
        val = ctx.get(self._key)
        if val is None:
            return False, f"key {self._key!r} not in context"
        try:
            val = float(val)
        except (TypeError, ValueError):
            return False, f"{self._key!r} is not numeric: {val!r}"
        if self._min_val is not None and val < self._min_val:
            return False, f"{self._key}={val} < min={self._min_val}"
        if self._max_val is not None and val > self._max_val:
            return False, f"{self._key}={val} > max={self._max_val}"
        return True, f"{self._key}={val} within bounds"


# ── ThresholdConstraint ───────────────────────────────────────────────────────

class ThresholdConstraint(StaticConstraint):
    """Validates that a numeric value is above or below a threshold."""

    def __init__(
        self,
        constraint_id:   str,
        name:            str,
        key:             str,
        threshold:       float,
        *,
        above:           bool = True,
        constraint_type: ConstraintType = ConstraintType.CUSTOM,
        mandatory:       bool = True,
    ) -> None:
        self._key       = key
        self._threshold = threshold
        self._above     = above
        super().__init__(
            constraint_id   = constraint_id,
            name            = name,
            validator       = self._threshold_check,
            constraint_type = constraint_type,
            mandatory       = mandatory,
        )

    def _threshold_check(self, ctx: EvaluationContext) -> tuple[bool, str]:
        val = ctx.get(self._key)
        if val is None:
            return False, f"key {self._key!r} not in context"
        try:
            val = float(val)
        except (TypeError, ValueError):
            return False, f"{self._key!r} is not numeric"
        if self._above and val < self._threshold:
            return False, f"{self._key}={val} < threshold={self._threshold}"
        if not self._above and val > self._threshold:
            return False, f"{self._key}={val} > threshold={self._threshold}"
        return True, f"{self._key}={val} meets threshold"
