"""
portfolio_optimization_factory.py — iios.portfolio.optimization
================================================================
Factory for creating requests, candidates, strategies, objectives,
and constraints with sensible defaults.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    DEFAULT_STRATEGY_NAME,
    AllocationCapability,
    ConstraintType,
    OptimizationObjective,
    OptimizationStrategyType,
    RebalancingCapability,
    ScoringMethod,
    VERSION,
)
from .portfolio_candidate import PortfolioCandidate
from .portfolio_constraint import PortfolioConstraint
from .portfolio_objective import PortfolioObjective
from .portfolio_optimization_context import OptimizationContext
from .portfolio_optimization_request import PortfolioOptimizationRequest
from .portfolio_optimization_strategy import PortfolioOptimizationStrategy


class PortfolioOptimizationFactory:
    """
    Factory class for creating core portfolio optimization objects.

    All methods are pure (no side effects, no state).
    """

    # ------------------------------------------------------------------
    # PortfolioOptimizationRequest
    # ------------------------------------------------------------------

    @staticmethod
    def create_request(
        portfolio_id:    str,
        *,
        strategy_name:   str = DEFAULT_STRATEGY_NAME,
        candidates:      Optional[List[PortfolioCandidate]] = None,
        inputs:          Optional[Dict[str, Any]] = None,
        optimization_id: str = "",
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> PortfolioOptimizationRequest:
        return PortfolioOptimizationRequest.create(
            portfolio_id,
            strategy_name   = strategy_name,
            candidates      = candidates,
            inputs          = inputs,
            optimization_id = optimization_id,
            metadata        = metadata,
        )

    # ------------------------------------------------------------------
    # PortfolioCandidate
    # ------------------------------------------------------------------

    @staticmethod
    def create_candidate(
        portfolio_id: str,
        *,
        candidate_id: str = "",
        inputs:       Optional[Dict[str, Any]] = None,
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> PortfolioCandidate:
        return PortfolioCandidate(
            candidate_id = candidate_id or str(uuid.uuid4()),
            portfolio_id = portfolio_id,
            inputs       = inputs,
            metadata     = metadata,
        )

    # ------------------------------------------------------------------
    # PortfolioOptimizationStrategy
    # ------------------------------------------------------------------

    @staticmethod
    def create_strategy(
        name:           str = DEFAULT_STRATEGY_NAME,
        *,
        strategy_id:    str = "",
        strategy_type:  OptimizationStrategyType = OptimizationStrategyType.EQUAL_WEIGHT,
        objectives:     Optional[List[PortfolioObjective]]  = None,
        constraints:    Optional[List[PortfolioConstraint]] = None,
        scoring_method: ScoringMethod = ScoringMethod.WEIGHTED,
        is_default:     bool = False,
    ) -> PortfolioOptimizationStrategy:
        return PortfolioOptimizationStrategy(
            strategy_id    = strategy_id or str(uuid.uuid4()),
            name           = name,
            strategy_type  = strategy_type,
            objectives     = objectives,
            constraints    = constraints,
            scoring_method = scoring_method,
            is_default     = is_default,
        )

    @staticmethod
    def create_default_strategy() -> PortfolioOptimizationStrategy:
        """
        Create the built-in default strategy (equal-weight, no constraints,
        single neutral objective).
        """
        neutral_obj = PortfolioOptimizationFactory.create_objective(
            objective_type = OptimizationObjective.MAXIMIZE_RISK_ADJUSTED_RETURN,
            name           = "default_neutral",
            fn             = lambda cand, inp: 0.5,
            weight         = 1.0,
        )
        return PortfolioOptimizationStrategy(
            strategy_id    = "default",
            name           = DEFAULT_STRATEGY_NAME,
            strategy_type  = OptimizationStrategyType.EQUAL_WEIGHT,
            objectives     = [neutral_obj],
            constraints    = [],
            scoring_method = ScoringMethod.WEIGHTED,
            is_default     = True,
        )

    # ------------------------------------------------------------------
    # PortfolioObjective
    # ------------------------------------------------------------------

    @staticmethod
    def create_objective(
        objective_type: OptimizationObjective,
        name:           str,
        fn:             Callable,
        *,
        weight:      float = 1.0,
        description: str   = "",
    ) -> PortfolioObjective:
        return PortfolioObjective(
            objective_type = objective_type,
            name           = name,
            fn             = fn,
            weight         = weight,
            description    = description,
        )

    # ------------------------------------------------------------------
    # PortfolioConstraint
    # ------------------------------------------------------------------

    @staticmethod
    def create_constraint(
        constraint_type: ConstraintType,
        name:            str,
        fn:              Callable,
        *,
        is_hard:     bool  = True,
        penalty:     float = 0.5,
        description: str   = "",
    ) -> PortfolioConstraint:
        return PortfolioConstraint(
            constraint_type = constraint_type,
            name            = name,
            fn              = fn,
            is_hard         = is_hard,
            penalty         = penalty,
            description     = description,
        )
