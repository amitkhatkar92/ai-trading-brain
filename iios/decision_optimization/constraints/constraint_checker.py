"""iios/decision_optimization/constraints/constraint_checker.py — Constraint ABC + implementations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from ..optimization_constants import ConstraintType
from ..optimization_context import Candidate


@dataclass
class ConstraintCheckResult:
    constraint_id: str
    satisfied:     bool
    is_hard:       bool  = True
    violation_msg: str   = ""
    severity:      float = 0.0   # 0.0 = no violation, 1.0 = maximum violation

    def to_dict(self) -> dict:
        return {
            "constraint_id": self.constraint_id,
            "satisfied":     self.satisfied,
            "is_hard":       self.is_hard,
            "violation_msg": self.violation_msg,
            "severity":      self.severity,
        }


class OptimizationConstraint(ABC):
    @property
    @abstractmethod
    def constraint_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.HARD

    @property
    def is_hard(self) -> bool:
        return self.constraint_type in (ConstraintType.HARD, ConstraintType.COMPLIANCE)

    @property
    def tags(self) -> list[str]:
        return []

    @abstractmethod
    def check(self, candidate: Candidate) -> ConstraintCheckResult: ...

    def to_dict(self) -> dict:
        return {
            "constraint_id":   self.constraint_id,
            "name":            self.name,
            "constraint_type": self.constraint_type.value,
            "is_hard":         self.is_hard,
            "tags":            self.tags,
        }


# ── ThresholdConstraint ───────────────────────────────────────────────────────

class ThresholdConstraint(OptimizationConstraint):
    """candidate.evaluation_score must be >= threshold."""

    def __init__(
        self,
        constraint_id:   str,
        name:            str,
        threshold:       float,
        *,
        constraint_type: ConstraintType = ConstraintType.HARD,
        tags:            list[str] | None = None,
    ) -> None:
        self._id        = constraint_id
        self._name      = name
        self._threshold = threshold
        self._type      = constraint_type
        self._tags      = tags or []

    @property
    def constraint_id(self) -> str:  return self._id
    @property
    def name(self) -> str:           return self._name
    @property
    def constraint_type(self) -> ConstraintType: return self._type
    @property
    def tags(self) -> list[str]:     return list(self._tags)

    def check(self, candidate: Candidate) -> ConstraintCheckResult:
        passed   = candidate.evaluation_score >= self._threshold
        severity = max(0.0, self._threshold - candidate.evaluation_score) if not passed else 0.0
        return ConstraintCheckResult(
            constraint_id = self._id,
            satisfied     = passed,
            is_hard       = self.is_hard,
            violation_msg = (
                f"score {candidate.evaluation_score:.4f} < threshold {self._threshold:.4f}"
                if not passed else ""
            ),
            severity      = severity,
        )


# ── BoundedConstraint ─────────────────────────────────────────────────────────

class BoundedConstraint(OptimizationConstraint):
    """lower <= candidate.get(key) <= upper."""

    def __init__(
        self,
        constraint_id:   str,
        name:            str,
        key:             str,
        lower:           float,
        upper:           float,
        *,
        constraint_type: ConstraintType = ConstraintType.HARD,
        tags:            list[str] | None = None,
    ) -> None:
        self._id    = constraint_id
        self._name  = name
        self._key   = key
        self._lower = lower
        self._upper = upper
        self._type  = constraint_type
        self._tags  = tags or []

    @property
    def constraint_id(self) -> str:  return self._id
    @property
    def name(self) -> str:           return self._name
    @property
    def constraint_type(self) -> ConstraintType: return self._type
    @property
    def tags(self) -> list[str]:     return list(self._tags)

    def check(self, candidate: Candidate) -> ConstraintCheckResult:
        try:
            val    = float(candidate.get(self._key, 0.0))
        except Exception:  # noqa: BLE001
            val    = 0.0
        passed = self._lower <= val <= self._upper
        return ConstraintCheckResult(
            constraint_id = self._id,
            satisfied     = passed,
            is_hard       = self.is_hard,
            violation_msg = (
                f"{self._key}={val:.4f} not in [{self._lower},{self._upper}]"
                if not passed else ""
            ),
        )


# ── PredicateConstraint ───────────────────────────────────────────────────────

class PredicateConstraint(OptimizationConstraint):
    """Custom callable predicate — must return True for the candidate to pass."""

    def __init__(
        self,
        constraint_id:   str,
        name:            str,
        predicate:       Callable[[Candidate], bool],
        *,
        constraint_type: ConstraintType = ConstraintType.HARD,
        tags:            list[str] | None = None,
    ) -> None:
        self._id        = constraint_id
        self._name      = name
        self._predicate = predicate
        self._type      = constraint_type
        self._tags      = tags or []

    @property
    def constraint_id(self) -> str:  return self._id
    @property
    def name(self) -> str:           return self._name
    @property
    def constraint_type(self) -> ConstraintType: return self._type
    @property
    def tags(self) -> list[str]:     return list(self._tags)

    def check(self, candidate: Candidate) -> ConstraintCheckResult:
        try:
            satisfied = bool(self._predicate(candidate))
            violation = "" if satisfied else "predicate returned False"
        except Exception as exc:  # noqa: BLE001
            satisfied = False
            violation = str(exc)
        return ConstraintCheckResult(
            constraint_id = self._id,
            satisfied     = satisfied,
            is_hard       = self.is_hard,
            violation_msg = violation,
        )
