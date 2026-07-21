"""
decision_solution_validator.py — iios.decision.optimization
============================================================
Validates a DecisionSolution for structural and logical integrity.

Seven validation checks (OptimizationValidationCode)

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import OptimizationValidationCode
from .decision_solution import DecisionSolution


@dataclass(frozen=True)
class SolutionValidationCheckResult:
    """Result of one validation check."""
    code:    OptimizationValidationCode
    passed:  bool
    message: str


@dataclass(frozen=True)
class SolutionValidationResult:
    """Aggregated result of all validation checks."""
    is_valid:      bool
    checks:        Tuple[SolutionValidationCheckResult, ...]
    failed_checks: Tuple[OptimizationValidationCode, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> Tuple[str, ...]:
        return tuple(c.message for c in self.checks if not c.passed)


class DecisionSolutionValidator:
    """
    Validates a :class:`DecisionSolution` against seven structural checks.
    """

    def validate(self, solution: DecisionSolution) -> SolutionValidationResult:
        checks = [
            self._check_candidate_validity(solution),
            self._check_objective_consistency(solution),
            self._check_constraint_consistency(solution),
            self._check_optimization_completeness(solution),
            self._check_ranking_integrity(solution),
            self._check_solution_integrity(solution),
            self._check_context_consistency(solution),
        ]
        failed = [c for c in checks if not c.passed]
        return SolutionValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = tuple(c.code for c in failed),
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )

    def _check_candidate_validity(self, s: DecisionSolution) -> SolutionValidationCheckResult:
        ok = (
            s.selected_candidate is not None
            and bool(s.selected_candidate.candidate_id)
            and bool(s.selected_candidate.symbol)
        )
        return SolutionValidationCheckResult(
            code    = OptimizationValidationCode.CANDIDATE_VALIDITY,
            passed  = ok,
            message = "" if ok else "selected_candidate is missing or has empty symbol/id",
        )

    def _check_objective_consistency(self, s: DecisionSolution) -> SolutionValidationCheckResult:
        ok = isinstance(s.objective_scores, dict)
        return SolutionValidationCheckResult(
            code    = OptimizationValidationCode.OBJECTIVE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "objective_scores must be a dict",
        )

    def _check_constraint_consistency(self, s: DecisionSolution) -> SolutionValidationCheckResult:
        ok = isinstance(s.constraint_violations, tuple)
        return SolutionValidationCheckResult(
            code    = OptimizationValidationCode.CONSTRAINT_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "constraint_violations must be a tuple",
        )

    def _check_optimization_completeness(self, s: DecisionSolution) -> SolutionValidationCheckResult:
        ok = bool(s.optimization_strategy) and s.evaluation_time_s >= 0.0
        return SolutionValidationCheckResult(
            code    = OptimizationValidationCode.OPTIMIZATION_COMPLETENESS,
            passed  = ok,
            message = "" if ok else "optimization_strategy is empty or evaluation_time_s is negative",
        )

    def _check_ranking_integrity(self, s: DecisionSolution) -> SolutionValidationCheckResult:
        ok = s.rank >= 1 and isinstance(s.rankings, tuple)
        return SolutionValidationCheckResult(
            code    = OptimizationValidationCode.RANKING_INTEGRITY,
            passed  = ok,
            message = "" if ok else f"rank must be ≥ 1, got {s.rank}",
        )

    def _check_solution_integrity(self, s: DecisionSolution) -> SolutionValidationCheckResult:
        ok = bool(s.solution_id) and bool(s.request_id)
        return SolutionValidationCheckResult(
            code    = OptimizationValidationCode.SOLUTION_INTEGRITY,
            passed  = ok,
            message = "" if ok else "solution_id or request_id is empty",
        )

    def _check_context_consistency(self, s: DecisionSolution) -> SolutionValidationCheckResult:
        ok = s.final_score >= 0.0
        return SolutionValidationCheckResult(
            code    = OptimizationValidationCode.CONTEXT_CONSISTENCY,
            passed  = ok,
            message = "" if ok else f"final_score must be ≥ 0.0, got {s.final_score}",
        )
