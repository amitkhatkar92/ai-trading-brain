"""iios/decision_optimization/optimization_factory.py — Convenience factory."""
from __future__ import annotations

from typing import Callable

from .optimization_constants import AlgorithmType, ConstraintType, ObjectiveType
from .optimization_context import Candidate
from .objectives.objective import PayloadObjective, ScoreObjective
from .objectives.objective_function import FunctionObjective
from .constraints.constraint_checker import (
    BoundedConstraint,
    PredicateConstraint,
    ThresholdConstraint,
)
from .optimization_manager import OptimizationRequest


class OptimizationFactory:
    """Convenience factory for creating optimization primitives."""

    @staticmethod
    def make_candidate(
        name: str = "",
        evaluation_score: float = 0.0,
        **payload,
    ) -> Candidate:
        return Candidate(
            name             = name,
            payload          = dict(payload),
            evaluation_score = evaluation_score,
        )

    @staticmethod
    def make_score_objective(
        objective_id:   str,
        name:           str = "score",
        *,
        objective_type: ObjectiveType = ObjectiveType.MAXIMIZE,
        weight:         float = 1.0,
    ) -> ScoreObjective:
        return ScoreObjective(
            objective_id   = objective_id,
            name           = name,
            objective_type = objective_type,
            weight         = weight,
        )

    @staticmethod
    def make_payload_objective(
        objective_id: str,
        name:         str,
        key:          str,
        *,
        objective_type: ObjectiveType = ObjectiveType.MAXIMIZE,
        weight:         float = 1.0,
        target_value:   float | None = None,
    ) -> PayloadObjective:
        return PayloadObjective(
            objective_id   = objective_id,
            name           = name,
            key            = key,
            objective_type = objective_type,
            weight         = weight,
            target_value   = target_value,
        )

    @staticmethod
    def make_function_objective(
        objective_id: str,
        name:         str,
        evaluator:    Callable[[Candidate], float],
        *,
        objective_type: ObjectiveType = ObjectiveType.MAXIMIZE,
        weight:         float = 1.0,
    ) -> FunctionObjective:
        return FunctionObjective(
            objective_id   = objective_id,
            name           = name,
            evaluator      = evaluator,
            objective_type = objective_type,
            weight         = weight,
        )

    @staticmethod
    def make_threshold_constraint(
        constraint_id:   str,
        name:            str,
        threshold:       float,
        *,
        constraint_type: ConstraintType = ConstraintType.HARD,
    ) -> ThresholdConstraint:
        return ThresholdConstraint(
            constraint_id   = constraint_id,
            name            = name,
            threshold       = threshold,
            constraint_type = constraint_type,
        )

    @staticmethod
    def make_bounded_constraint(
        constraint_id: str,
        name:          str,
        key:           str,
        lower:         float,
        upper:         float,
        *,
        constraint_type: ConstraintType = ConstraintType.HARD,
    ) -> BoundedConstraint:
        return BoundedConstraint(
            constraint_id   = constraint_id,
            name            = name,
            key             = key,
            lower           = lower,
            upper           = upper,
            constraint_type = constraint_type,
        )

    @staticmethod
    def make_predicate_constraint(
        constraint_id:   str,
        name:            str,
        predicate:       Callable[[Candidate], bool],
        *,
        constraint_type: ConstraintType = ConstraintType.HARD,
    ) -> PredicateConstraint:
        return PredicateConstraint(
            constraint_id   = constraint_id,
            name            = name,
            predicate       = predicate,
            constraint_type = constraint_type,
        )

    @staticmethod
    def make_request(
        candidates: list,
        objectives: list | None = None,
        constraints: list | None = None,
        **kwargs,
    ) -> OptimizationRequest:
        return OptimizationRequest(
            candidates  = candidates,
            objectives  = objectives or [],
            constraints = constraints or [],
            **kwargs,
        )
