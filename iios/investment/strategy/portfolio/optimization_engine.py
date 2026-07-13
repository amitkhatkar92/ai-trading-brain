"""iios/investment/strategy/portfolio/optimization_engine.py
OptimizationEngine — applies constraint solving and refinement to a portfolio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.strategy_portfolio import StrategyPortfolio, PortfolioState
from iios.investment.strategy.portfolio.strategy_allocation import AllocationStatus
from iios.investment.strategy.portfolio.construction_constraints import ConstructionConstraints
from iios.investment.strategy.portfolio.constraint_solver import ConstraintSolver, SolverResult
from iios.investment.strategy.portfolio.optimization_statistics import (
    concentration_score, coverage_score, target_tracking_error
)


@dataclass(frozen=True)
class OptimizationResult:
    portfolio_id:        str
    optimized_weights:   Dict[str, float]
    previous_weights:    Dict[str, float]
    tracking_error:      float
    concentration_score: float
    coverage_score:      float
    solver_converged:    bool
    warnings:            List[str]
    optimized_at:        datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        return self.solver_converged and abs(sum(self.optimized_weights.values()) - 1.0) < 1e-6

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":        self.portfolio_id,
            "tracking_error":      round(self.tracking_error, 6),
            "concentration_score": round(self.concentration_score, 4),
            "coverage_score":      round(self.coverage_score, 4),
            "solver_converged":    self.solver_converged,
            "weight_count":        len(self.optimized_weights),
            "warnings":            self.warnings,
            "optimized_at":        self.optimized_at.isoformat(),
        }


class OptimizationEngine:
    """
    Takes an already-constructed portfolio and applies constraint solving
    to produce the best feasible weight assignment.
    """

    def __init__(
        self,
        solver: Optional[ConstraintSolver] = None,
    ) -> None:
        self._solver = solver or ConstraintSolver()

    def optimize(
        self,
        portfolio:   StrategyPortfolio,
        constraints: ConstructionConstraints,
    ) -> OptimizationResult:
        """
        Resolve weight constraints on an existing portfolio and update
        allocation weights in place.  Returns an OptimizationResult.
        """
        active = portfolio.active_allocations()
        if not active:
            return OptimizationResult(
                portfolio_id=portfolio.portfolio_id,
                optimized_weights={},
                previous_weights={},
                tracking_error=0.0,
                concentration_score=1.0,
                coverage_score=0.0,
                solver_converged=False,
                warnings=["No active allocations to optimize"],
            )

        previous_weights = {a.strategy_id: a.weight for a in active}
        raw = {a.strategy_id: a.target_weight or a.weight for a in active}

        result: SolverResult = self._solver.solve(raw, constraints)

        # Check concentration
        _, conc = self._solver.check_concentration(result.weights, constraints)
        warnings = list(result.warnings)
        if conc > constraints.max_concentration:
            warnings.append(
                f"Top-3 concentration {conc:.2%} exceeds limit {constraints.max_concentration:.2%}"
            )

        # Apply optimized weights back to allocations
        now = datetime.now(timezone.utc)
        for sid, w in result.weights.items():
            if sid in portfolio.allocations:
                alloc = portfolio.allocations[sid]
                alloc.weight = w
                alloc.target_weight = w
                alloc.updated_at = now

        # Remove allocations that were dropped by the solver
        dropped = set(previous_weights.keys()) - set(result.weights.keys())
        for sid in dropped:
            if sid in portfolio.allocations:
                portfolio.allocations[sid].status = AllocationStatus.REMOVED

        portfolio.last_optimized = now
        portfolio._touch()

        weights_list = list(result.weights.values())
        vols_proxy   = [1.0] * len(weights_list)   # placeholder for coverage check

        return OptimizationResult(
            portfolio_id=portfolio.portfolio_id,
            optimized_weights=result.weights,
            previous_weights=previous_weights,
            tracking_error=target_tracking_error(result.weights, previous_weights),
            concentration_score=concentration_score(weights_list),
            coverage_score=coverage_score(
                weights_list, constraints.min_weight, constraints.max_weight
            ),
            solver_converged=result.converged,
            warnings=warnings,
        )
