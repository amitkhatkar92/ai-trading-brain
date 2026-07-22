"""
portfolio_solution_validator.py — iios.portfolio.optimization
=============================================================
Validates a PortfolioSolution for internal integrity.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .portfolio_solution import PortfolioSolution

# Allocation sum tolerance
_SUM_TOLERANCE: float = 1e-4


@dataclass(frozen=True)
class SolutionValidationResult:
    """Result of solution integrity checks."""
    solution_id:   str
    is_valid:      bool
    passed_checks: tuple   # Tuple[str, ...]
    failed_checks: tuple   # Tuple[str, ...]
    message:       str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "solution_id":   self.solution_id,
            "is_valid":      self.is_valid,
            "passed_checks": list(self.passed_checks),
            "failed_checks": list(self.failed_checks),
            "message":       self.message,
        }


class PortfolioSolutionValidator:
    """
    Performs 8 integrity checks on a PortfolioSolution.

    Checks
    ------
    1. solution_id is non-empty.
    2. optimization_id is non-empty.
    3. candidate_id is non-empty.
    4. portfolio_id is non-empty.
    5. score is in [0.0, 1.0].
    6. rank >= 0.
    7. If allocation_plan is present, its total > 0.
    8. If feasible and selected, score > 0.0.
    """

    def validate(self, solution: PortfolioSolution) -> SolutionValidationResult:
        passed: List[str] = []
        failed: List[str] = []

        def check(name: str, condition: bool) -> None:
            (passed if condition else failed).append(name)

        check("solution_id_non_empty",    bool(solution.solution_id))
        check("optimization_id_non_empty", bool(solution.optimization_id))
        check("candidate_id_non_empty",   bool(solution.candidate_id))
        check("portfolio_id_non_empty",   bool(solution.portfolio_id))
        check("score_in_range",           0.0 <= solution.score <= 1.0)
        check("rank_non_negative",        solution.rank >= 0)
        check(
            "allocation_plan_total_positive",
            solution.allocation_plan is None or solution.allocation_plan.total > 0,
        )
        check(
            "selected_implies_positive_score",
            not (solution.is_feasible and solution.is_selected)
            or solution.score > 0.0,
        )

        is_valid = len(failed) == 0
        message  = (
            "all checks passed"
            if is_valid
            else f"failed checks: {', '.join(failed)}"
        )

        return SolutionValidationResult(
            solution_id   = solution.solution_id,
            is_valid      = is_valid,
            passed_checks = tuple(passed),
            failed_checks = tuple(failed),
            message       = message,
        )
