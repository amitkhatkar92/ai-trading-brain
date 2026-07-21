"""
decision_optimization_factory.py — iios.decision.optimization
==============================================================
Stateless factory for all optimization framework objects.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    DEFAULT_STRATEGY_ID,
    ConstraintOperator,
    ConstraintType,
    OptimizationObjectiveType,
    OptimizationStrategyType,
)
from .decision_candidate import DecisionCandidate
from .decision_constraint import DecisionConstraint
from .decision_objective  import DecisionObjective
from .decision_optimization_context import DecisionOptimizationContext
from .decision_optimization_request import DecisionOptimizationRequest
from .decision_optimization_strategy import DecisionOptimizationStrategy


class DecisionOptimizationFactory:
    """Stateless factory for constructing optimization framework objects."""

    # ------------------------------------------------------------------
    # Candidate
    # ------------------------------------------------------------------

    def create_candidate(
        self,
        symbol:             str,
        direction:          str,
        quantity:           float,
        price:              float,
        expected_return:    float,
        risk_score:         float,
        confidence:         float,
        *,
        candidate_id:       Optional[str]  = None,
        decision_id:        str            = "",
        liquidity_score:    float          = 0.5,
        execution_cost:     float          = 0.0,
        portfolio_exposure: float          = 0.0,
        source:             str            = "",
        metadata:           Optional[Dict] = None,
    ) -> DecisionCandidate:
        return DecisionCandidate.create(
            symbol             = symbol,
            direction          = direction,
            quantity           = quantity,
            price              = price,
            expected_return    = expected_return,
            risk_score         = risk_score,
            confidence         = confidence,
            candidate_id       = candidate_id,
            decision_id        = decision_id,
            liquidity_score    = liquidity_score,
            execution_cost     = execution_cost,
            portfolio_exposure = portfolio_exposure,
            source             = source,
            metadata           = metadata,
        )

    # ------------------------------------------------------------------
    # Objective
    # ------------------------------------------------------------------

    def create_objective(
        self,
        name:             str,
        objective_type:   OptimizationObjectiveType,
        *,
        objective_id:     Optional[str]                     = None,
        weight:           float                              = 1.0,
        target_field:     str                                = "",
        description:      str                                = "",
        custom_evaluator: Optional[Callable[[dict], float]] = None,
    ) -> DecisionObjective:
        return DecisionObjective.create(
            name             = name,
            objective_type   = objective_type,
            objective_id     = objective_id,
            weight           = weight,
            target_field     = target_field,
            description      = description,
            custom_evaluator = custom_evaluator,
        )

    # ------------------------------------------------------------------
    # Constraint
    # ------------------------------------------------------------------

    def create_constraint(
        self,
        name:          str,
        constraint_type: ConstraintType,
        operator:      ConstraintOperator,
        field_path:    str,
        threshold:     float,
        *,
        constraint_id: Optional[str]                     = None,
        threshold_max: float                              = 0.0,
        penalty:       float                              = 0.5,
        is_hard:       bool                               = True,
        description:   str                                = "",
        custom_evaluator: Optional[Callable[[dict], bool]] = None,
    ) -> DecisionConstraint:
        return DecisionConstraint.create(
            name             = name,
            constraint_type  = constraint_type,
            operator         = operator,
            field_path       = field_path,
            threshold        = threshold,
            constraint_id    = constraint_id,
            threshold_max    = threshold_max,
            penalty          = penalty,
            is_hard          = is_hard,
            description      = description,
            custom_evaluator = custom_evaluator,
        )

    # ------------------------------------------------------------------
    # Strategy
    # ------------------------------------------------------------------

    def create_strategy(
        self,
        name:            str,
        strategy_type:   OptimizationStrategyType,
        *,
        strategy_id:     Optional[str]     = None,
        config:          Optional[Dict]     = None,
        description:     str               = "",
        custom_callable: Optional[Callable] = None,
    ) -> DecisionOptimizationStrategy:
        return DecisionOptimizationStrategy.create(
            name             = name,
            strategy_type    = strategy_type,
            strategy_id      = strategy_id,
            config           = config,
            description      = description,
            custom_callable  = custom_callable,
        )

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def create_context(
        self,
        *,
        context_id:    Optional[str]  = None,
        request_id:    str             = "",
        decision_id:   str             = "",
        session_id:    str             = "",
        pipeline_id:   str             = "",
        policy_result: Optional[Dict]  = None,
        inputs:        Optional[Dict]  = None,
        snapshots:     Optional[Dict]  = None,
        metadata:      Optional[Dict]  = None,
    ) -> DecisionOptimizationContext:
        return DecisionOptimizationContext.create(
            context_id    = context_id,
            request_id    = request_id,
            decision_id   = decision_id,
            session_id    = session_id,
            pipeline_id   = pipeline_id,
            policy_result = policy_result,
            inputs        = inputs,
            snapshots     = snapshots,
            metadata      = metadata,
        )

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    def create_request(
        self,
        context:        DecisionOptimizationContext,
        candidates:     List[DecisionCandidate],
        *,
        request_id:     Optional[str]       = None,
        strategy_id:    str                 = DEFAULT_STRATEGY_ID,
        objective_ids:  Optional[List[str]] = None,
        constraint_ids: Optional[List[str]] = None,
        metadata:       Optional[Dict]       = None,
    ) -> DecisionOptimizationRequest:
        return DecisionOptimizationRequest.create(
            context        = context,
            candidates     = candidates,
            request_id     = request_id,
            strategy_id    = strategy_id,
            objective_ids  = objective_ids,
            constraint_ids = constraint_ids,
            metadata       = metadata,
        )
