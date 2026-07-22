"""
portfolio_constraint_engine.py — iios.portfolio.optimization
=============================================================
Evaluates a list of portfolio constraints against a candidate.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .portfolio_candidate import PortfolioCandidate
from .portfolio_constraint import ConstraintResult, PortfolioConstraint


class PortfolioConstraintEngine:
    """
    Evaluates all constraints against a portfolio candidate.

    The engine delegates individual evaluation to each
    ``PortfolioConstraint`` and aggregates the results.
    """

    def evaluate(
        self,
        candidate:   PortfolioCandidate,
        constraints: List[PortfolioConstraint],
        inputs:      Dict[str, Any],
    ) -> List[ConstraintResult]:
        """
        Evaluate all constraints against *candidate*.

        Returns a list of ConstraintResult objects (one per constraint).
        Exceptions within individual constraint functions are caught and
        recorded as violations — they never propagate.
        """
        results: List[ConstraintResult] = []
        for constraint in constraints:
            result = constraint.evaluate(candidate, inputs)
            results.append(result)
        return results

    def is_feasible(self, results: List[ConstraintResult]) -> bool:
        """
        Return True when no hard constraint is violated.

        Soft constraints (is_hard=False) do NOT affect feasibility.
        """
        return all(r.satisfied or not r.is_hard for r in results)

    def total_penalty(self, results: List[ConstraintResult]) -> float:
        """Sum of soft-constraint penalties for violated constraints."""
        return sum(r.penalty for r in results if not r.satisfied and not r.is_hard)

    def violated_names(self, results: List[ConstraintResult]) -> List[str]:
        """Return constraint names that were violated (hard or soft)."""
        return [r.constraint_name for r in results if not r.satisfied]

    def satisfied_count(self, results: List[ConstraintResult]) -> int:
        return sum(1 for r in results if r.satisfied)

    def violated_count(self, results: List[ConstraintResult]) -> int:
        return sum(1 for r in results if not r.satisfied)
