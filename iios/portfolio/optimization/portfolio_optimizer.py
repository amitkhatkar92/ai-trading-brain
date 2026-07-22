"""
portfolio_optimizer.py — iios.portfolio.optimization
=====================================================
Core optimization pipeline — orchestrates all engines to produce a
ranked list of PortfolioSolution objects and select the best one.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION, AllocationCapability, RebalancingCapability
from .portfolio_allocation_engine import PortfolioAllocationEngine
from .portfolio_candidate import PortfolioCandidate
from .portfolio_constraint_engine import PortfolioConstraintEngine
from .portfolio_optimization_strategy import PortfolioOptimizationStrategy
from .portfolio_priority_engine import PortfolioPriorityEngine
from .portfolio_ranking_engine import PortfolioRankingEngine
from .portfolio_rebalancing_engine import PortfolioRebalancingEngine
from .portfolio_scoring_engine import PortfolioScoringEngine
from .portfolio_solution import PortfolioSolution
from .portfolio_solution_selector import PortfolioSolutionSelector
from .portfolio_solution_validator import PortfolioSolutionValidator


class PortfolioOptimizer:
    """
    Core optimization pipeline.

    Accepts a list of policy-approved candidates and an optimization
    strategy.  Produces a ranked, annotated list of PortfolioSolution
    objects and identifies the optimal selection.

    Pipeline
    --------
    1. For each candidate:
       a. Evaluate constraints  (ConstraintEngine)
       b. Generate allocation   (AllocationEngine)
       c. Generate rebalancing  (RebalancingEngine)
       d. Score candidate       (ScoringEngine)
       e. Build PortfolioSolution
    2. Rank all solutions       (RankingEngine)
    3. Apply priority rules     (PriorityEngine)
    4. Select optimal solution  (SolutionSelector)
    5. Return (ranked_solutions, selected_solution)
    """

    def __init__(self) -> None:
        self._constraint_engine  = PortfolioConstraintEngine()
        self._allocation_engine  = PortfolioAllocationEngine()
        self._rebalancing_engine = PortfolioRebalancingEngine()
        self._scoring_engine     = PortfolioScoringEngine()
        self._ranking_engine     = PortfolioRankingEngine()
        self._priority_engine    = PortfolioPriorityEngine()
        self._selector           = PortfolioSolutionSelector()
        self._validator          = PortfolioSolutionValidator()

    def optimize(
        self,
        optimization_id: str,
        candidates:      List[PortfolioCandidate],
        strategy:        PortfolioOptimizationStrategy,
        inputs:          Dict[str, Any],
    ) -> Tuple[List[PortfolioSolution], Optional[PortfolioSolution]]:
        """
        Run the full optimization pipeline.

        Returns
        -------
        (ranked_solutions, selected_solution)

        ``selected_solution`` is None if no feasible candidate exists.
        """
        solutions: List[PortfolioSolution] = []

        for candidate in candidates:
            sol = self._evaluate_candidate(
                candidate, strategy, inputs, optimization_id
            )
            solutions.append(sol)

        ranked    = self._ranking_engine.rank(solutions)
        final     = self._priority_engine.apply_priority(ranked)
        selected  = self._selector.select(final)

        return final, selected

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _evaluate_candidate(
        self,
        candidate:       PortfolioCandidate,
        strategy:        PortfolioOptimizationStrategy,
        inputs:          Dict[str, Any],
        optimization_id: str,
    ) -> PortfolioSolution:
        merged = {**inputs, **candidate.inputs}

        # 1. Constraints
        constraint_results = self._constraint_engine.evaluate(
            candidate, strategy.constraints, merged
        )
        is_feasible = self._constraint_engine.is_feasible(constraint_results)

        # 2. Allocation
        alloc_plan = self._allocation_engine.generate(
            candidate, strategy, merged, AllocationCapability.CAPITAL
        )

        # 3. Rebalancing
        rebal_plan = self._rebalancing_engine.generate(
            candidate, strategy, merged, RebalancingCapability.THRESHOLD
        )

        # 4. Score
        score = self._scoring_engine.score(
            candidate,
            strategy.objectives,
            constraint_results,
            merged,
            strategy.scoring_method,
        )

        # 5. Objective scores dict
        obj_results = self._scoring_engine.objective_results(
            candidate, strategy.objectives, merged
        )
        objective_scores = {r.objective_name: r.score for r in obj_results}

        reason = (
            "feasible, selected for optimization"
            if is_feasible
            else f"infeasible: {', '.join(self._constraint_engine.violated_names(constraint_results)) or 'unknown'}"
        )

        solution = PortfolioSolution(
            solution_id            = str(uuid.uuid4()),
            optimization_id        = optimization_id,
            candidate_id           = candidate.candidate_id,
            portfolio_id           = candidate.portfolio_id,
            strategy_name          = strategy.name,
            objectives_evaluated   = len(strategy.objectives),
            constraints_satisfied  = self._constraint_engine.satisfied_count(constraint_results),
            constraints_violated   = self._constraint_engine.violated_count(constraint_results),
            allocation_plan        = alloc_plan,
            rebalancing_plan       = rebal_plan,
            score                  = score,
            is_feasible            = is_feasible,
            reason                 = reason,
            constraint_violations  = self._constraint_engine.violated_names(constraint_results),
            objective_scores       = objective_scores,
            evaluated_at           = time.time(),
            framework_version      = VERSION,
        )

        return solution
