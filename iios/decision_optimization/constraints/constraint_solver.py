"""iios/decision_optimization/constraints/constraint_solver.py"""
from __future__ import annotations

from ..optimization_context import Candidate
from .constraint_checker import ConstraintCheckResult, OptimizationConstraint


class ConstraintSolver:
    """Evaluates all constraints for every candidate."""

    def solve(
        self,
        candidates:  list[Candidate],
        constraints: list[OptimizationConstraint],
    ) -> dict[str, list[ConstraintCheckResult]]:
        """Returns {candidate_id: [check_results]}."""
        result: dict[str, list[ConstraintCheckResult]] = {}
        for cand in candidates:
            checks: list[ConstraintCheckResult] = []
            for c in constraints:
                try:
                    checks.append(c.check(cand))
                except Exception as exc:  # noqa: BLE001
                    checks.append(ConstraintCheckResult(
                        constraint_id = c.constraint_id,
                        satisfied     = False,
                        is_hard       = c.is_hard,
                        violation_msg = str(exc),
                        severity      = 1.0,
                    ))
            result[cand.candidate_id] = checks
        return result

    def is_feasible(
        self,
        candidate:   Candidate,
        constraints: list[OptimizationConstraint],
    ) -> bool:
        """True if candidate satisfies all hard constraints."""
        for c in constraints:
            if not c.is_hard:
                continue
            try:
                result = c.check(candidate)
            except Exception:  # noqa: BLE001
                return False
            if not result.satisfied:
                return False
        return True

    def hard_violations(
        self,
        candidate:   Candidate,
        constraints: list[OptimizationConstraint],
    ) -> list[ConstraintCheckResult]:
        """Return all hard-constraint violations for this candidate."""
        violations: list[ConstraintCheckResult] = []
        for c in constraints:
            if not c.is_hard:
                continue
            try:
                r = c.check(candidate)
                if not r.satisfied:
                    violations.append(r)
            except Exception as exc:  # noqa: BLE001
                violations.append(ConstraintCheckResult(
                    constraint_id = c.constraint_id,
                    satisfied     = False,
                    is_hard       = True,
                    violation_msg = str(exc),
                ))
        return violations

    def soft_penalty(
        self,
        candidate:   Candidate,
        constraints: list[OptimizationConstraint],
    ) -> float:
        """Sum of severity scores from violated soft constraints."""
        total = 0.0
        for c in constraints:
            if c.is_hard:
                continue
            try:
                r = c.check(candidate)
                if not r.satisfied:
                    total += r.severity
            except Exception:  # noqa: BLE001
                total += 1.0
        return total
