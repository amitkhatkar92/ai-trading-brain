"""
decision_constraint_engine.py — iios.decision.optimization
===========================================================
Evaluates all constraints for a candidate.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Dict, List

from iios.common.logging.logging_manager import get_logger

from .decision_candidate  import DecisionCandidate
from .decision_constraint import (
    ConstraintCheckResult,
    ConstraintEvaluationResult,
    DecisionConstraint,
)
from .decision_optimization_context import DecisionOptimizationContext

_log = get_logger(__name__)


class DecisionConstraintEngine:
    """
    Evaluates a list of :class:`DecisionConstraint` objects against a
    :class:`DecisionCandidate`.

    Hard constraint violations mark the candidate infeasible.
    Soft constraint violations accumulate a penalty score.
    """

    def evaluate_all(
        self,
        candidate:   DecisionCandidate,
        constraints: List[DecisionConstraint],
        context:     DecisionOptimizationContext,
    ) -> ConstraintEvaluationResult:
        """
        Check all constraints and return an aggregate result.

        The evaluation data dict merges candidate fields and context data,
        giving constraints access to all available information.
        """
        # Merge candidate data + context data
        data: dict = {**candidate.to_dict(), **context.to_dict()}

        checks: List[ConstraintCheckResult] = []
        violated_hard: List[str] = []
        violated_soft: List[str] = []
        total_penalty  = 0.0

        for constraint in constraints:
            try:
                satisfied = constraint.is_satisfied(data)
            except Exception as exc:
                _log.warning(
                    f"DecisionConstraintEngine: error checking constraint "
                    f"{constraint.constraint_id!r} for candidate "
                    f"{candidate.candidate_id!r}: {exc}"
                )
                # Treat evaluation error as a failed constraint
                satisfied = False

            penalty = 0.0
            if not satisfied:
                if constraint.is_hard:
                    violated_hard.append(constraint.name)
                else:
                    violated_soft.append(constraint.name)
                    penalty = constraint.penalty
                    total_penalty += penalty

            checks.append(ConstraintCheckResult(
                constraint_id   = constraint.constraint_id,
                constraint_name = constraint.name,
                is_hard         = constraint.is_hard,
                satisfied       = satisfied,
                penalty_applied = penalty,
            ))

        is_feasible = len(violated_hard) == 0

        return ConstraintEvaluationResult(
            candidate_id  = candidate.candidate_id,
            checks        = tuple(checks),
            violated_hard = tuple(violated_hard),
            violated_soft = tuple(violated_soft),
            total_penalty = total_penalty,
            is_feasible   = is_feasible,
        )
