"""iios/investment/strategy/portfolio/constraint_solver.py
ConstraintSolver — iterative projection that enforces weight constraints.
Operates on Dict[strategy_id, weight] (mutable).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from iios.investment.strategy.portfolio.construction_constraints import ConstructionConstraints
from iios.investment.strategy.portfolio.portfolio_statistics import project_weights


@dataclass(frozen=True)
class SolverResult:
    weights:         Dict[str, float]
    converged:       bool
    iterations_used: int
    residual:        float     # abs(sum - 1.0) after convergence
    warnings:        List[str] = field(default_factory=list)


class ConstraintSolver:
    """
    Projects an arbitrary weight dict onto the feasible simplex:
      • each weight ∈ [min_weight, max_weight]
      • sum = 1.0
      • count ≤ max_strategies (lowest weights dropped if over budget)

    Uses the iterative clamping algorithm from portfolio_statistics.project_weights
    but adds strategy-count enforcement and concentration checking.
    """

    def __init__(self, max_iter: int = 100, tol: float = 1e-8) -> None:
        self._max_iter = max_iter
        self._tol = tol

    def solve(
        self,
        raw_weights:  Dict[str, float],
        constraints:  ConstructionConstraints,
    ) -> SolverResult:
        if not raw_weights:
            return SolverResult({}, False, 0, 1.0, ["empty weight set"])

        warnings: List[str] = []

        # 1. Drop zero / negative weights
        trimmed = {k: max(v, 0.0) for k, v in raw_weights.items() if v > 0.0}
        if not trimmed:
            # All weights non-positive — fall back to equal weight
            n = len(raw_weights)
            equal = {k: 1.0 / n for k in raw_weights}
            trimmed = equal
            warnings.append("All raw weights non-positive; fell back to equal weight")

        # 2. Enforce max_strategies by dropping lowest-weight strategies
        if len(trimmed) > constraints.max_strategies:
            sorted_ids = sorted(trimmed, key=lambda k: trimmed[k], reverse=True)
            dropped = sorted_ids[constraints.max_strategies:]
            trimmed = {k: v for k, v in trimmed.items() if k not in dropped}
            warnings.append(f"Dropped {len(dropped)} strategies to meet max_strategies limit")

        # 3. Iterative projection
        projected = project_weights(
            trimmed,
            min_w=constraints.min_weight,
            max_w=constraints.max_weight,
            max_iter=self._max_iter,
        )

        residual = abs(sum(projected.values()) - 1.0)
        converged = residual < self._tol

        return SolverResult(
            weights=projected,
            converged=converged,
            iterations_used=self._max_iter,   # internal iters not exposed
            residual=residual,
            warnings=warnings,
        )

    def check_concentration(
        self,
        weights:     Dict[str, float],
        constraints: ConstructionConstraints,
        top_n:       int = 3,
    ) -> Tuple[bool, float]:
        """
        Returns (passes, top_n_concentration).
        Fails if top_n combined weight > max_concentration.
        """
        top_weights = sorted(weights.values(), reverse=True)[:top_n]
        concentration = sum(top_weights)
        passes = concentration <= constraints.max_concentration
        return passes, concentration
