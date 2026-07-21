"""
decision_constraint.py — iios.decision.optimization
=====================================================
DecisionConstraint        — a single feasibility requirement.
ConstraintCheckResult     — result of checking one constraint.
ConstraintEvaluationResult — aggregate of all constraint checks for a candidate.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .constants import ConstraintOperator, ConstraintType


# ---------------------------------------------------------------------------
# Constraint
# ---------------------------------------------------------------------------

def _navigate(data: dict, path: str, default: Any = None) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


@dataclass
class DecisionConstraint:
    """
    A single feasibility requirement that a candidate must satisfy.

    Hard constraints (``is_hard=True``) render a candidate **infeasible**
    when violated.  Soft constraints contribute a ``penalty`` to the score
    but do not disqualify the candidate.

    Parameters
    ----------
    constraint_id :   Unique identifier.
    name :            Human-readable name.
    constraint_type : Category (risk, capital, etc.).
    operator :        Comparison operator.
    field_path :      Dotted path into candidate data or context dict.
    threshold :       Comparison value (lower bound for BETWEEN).
    threshold_max :   Upper bound for BETWEEN operator.
    penalty :         Score penalty applied for soft constraint violations.
    is_hard :         If ``True``, violation → infeasible.
    description :     Optional explanation.
    """

    constraint_id: str
    name:          str
    constraint_type: ConstraintType
    operator:      ConstraintOperator
    field_path:    str
    threshold:     float
    threshold_max: float              = 0.0
    penalty:       float              = 0.5
    is_hard:       bool               = True
    description:   str                = ""
    _custom_evaluator: Optional[Callable[[dict], bool]] = field(
        default=None, repr=False, compare=False
    )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def is_satisfied(self, data: dict) -> bool:
        """Return ``True`` if the constraint is satisfied for *data*."""
        if self._custom_evaluator is not None:
            try:
                return bool(self._custom_evaluator(data))
            except Exception:
                return False

        op = self.operator

        if op == ConstraintOperator.EXISTS:
            return _navigate(data, self.field_path) is not None
        if op == ConstraintOperator.NOT_EXISTS:
            return _navigate(data, self.field_path) is None

        value = _navigate(data, self.field_path)
        if value is None:
            return False

        try:
            v = float(value)
            t = float(self.threshold)
            if op == ConstraintOperator.LT:
                return v < t
            if op == ConstraintOperator.LTE:
                return v <= t
            if op == ConstraintOperator.GT:
                return v > t
            if op == ConstraintOperator.GTE:
                return v >= t
            if op == ConstraintOperator.EQ:
                return v == t
            if op == ConstraintOperator.BETWEEN:
                return t <= v <= float(self.threshold_max)
        except (TypeError, ValueError):
            return False

        return False

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:          str,
        constraint_type: ConstraintType,
        operator:      ConstraintOperator,
        field_path:    str,
        threshold:     float,
        *,
        constraint_id: Optional[str]                   = None,
        threshold_max: float                            = 0.0,
        penalty:       float                            = 0.5,
        is_hard:       bool                             = True,
        description:   str                              = "",
        custom_evaluator: Optional[Callable[[dict], bool]] = None,
    ) -> "DecisionConstraint":
        return cls(
            constraint_id     = constraint_id or str(uuid.uuid4()),
            name              = name,
            constraint_type   = constraint_type,
            operator          = operator,
            field_path        = field_path,
            threshold         = threshold,
            threshold_max     = threshold_max,
            penalty           = penalty,
            is_hard           = is_hard,
            description       = description,
            _custom_evaluator = custom_evaluator,
        )


# ---------------------------------------------------------------------------
# Constraint check & evaluation results
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConstraintCheckResult:
    """Result of evaluating one constraint against one candidate."""
    constraint_id:   str
    constraint_name: str
    is_hard:         bool
    satisfied:       bool
    penalty_applied: float


@dataclass(frozen=True)
class ConstraintEvaluationResult:
    """
    Aggregated result of checking all constraints against one candidate.

    Parameters
    ----------
    candidate_id :      ID of the evaluated candidate.
    checks :            Individual check results.
    violated_hard :     Names of hard constraints that were violated.
    violated_soft :     Names of soft constraints that were violated.
    total_penalty :     Sum of penalties from soft violations.
    is_feasible :       ``True`` if no hard constraints were violated.
    """

    candidate_id:   str
    checks:         Tuple[ConstraintCheckResult, ...]
    violated_hard:  Tuple[str, ...]
    violated_soft:  Tuple[str, ...]
    total_penalty:  float
    is_feasible:    bool

    @property
    def total_violations(self) -> int:
        return len(self.violated_hard) + len(self.violated_soft)
