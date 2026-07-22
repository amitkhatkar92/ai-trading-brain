"""
portfolio_optimization_strategy.py — iios.portfolio.optimization
================================================================
PortfolioOptimizationStrategy — named strategy holding objectives
and constraints used by the optimization pipeline.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_STRATEGY_NAME,
    OptimizationStrategyType,
    ScoringMethod,
    StrategyStatus,
    VERSION,
)
from .portfolio_constraint import PortfolioConstraint
from .portfolio_objective import PortfolioObjective


class PortfolioOptimizationStrategy:
    """
    Named optimization strategy.

    A strategy pairs a list of objectives (what to optimize) with a
    list of constraints (what must hold) and a scoring method.

    Parameters
    ----------
    strategy_id :    Unique identifier (auto-generated if omitted).
    name :           Human-readable name (used for lookup).
    strategy_type :  Algorithmic style (e.g., MEAN_VARIANCE_OPTIMIZATION).
    objectives :     List of PortfolioObjective objects.
    constraints :    List of PortfolioConstraint objects.
    scoring_method : How objective scores are aggregated.
    is_default :     Whether this strategy is the fallback strategy.
    description :    Optional strategy description.
    """

    def __init__(
        self,
        strategy_id:    str = "",
        name:           str = DEFAULT_STRATEGY_NAME,
        *,
        strategy_type:  OptimizationStrategyType = OptimizationStrategyType.EQUAL_WEIGHT,
        objectives:     Optional[List[PortfolioObjective]]  = None,
        constraints:    Optional[List[PortfolioConstraint]] = None,
        scoring_method: ScoringMethod = ScoringMethod.WEIGHTED,
        is_default:     bool = False,
        description:    str  = "",
    ) -> None:
        if not name:
            raise ValueError("PortfolioOptimizationStrategy requires a non-empty name")
        self._strategy_id   = strategy_id or str(uuid.uuid4())
        self._name          = name
        self._strategy_type = strategy_type
        self._objectives:   List[PortfolioObjective]  = list(objectives or [])
        self._constraints:  List[PortfolioConstraint] = list(constraints or [])
        self._scoring_method = scoring_method
        self._is_default    = is_default
        self._description   = description
        self._status        = StrategyStatus.ACTIVE

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def strategy_type(self) -> OptimizationStrategyType:
        return self._strategy_type

    @property
    def objectives(self) -> List[PortfolioObjective]:
        return list(self._objectives)

    @property
    def constraints(self) -> List[PortfolioConstraint]:
        return list(self._constraints)

    @property
    def scoring_method(self) -> ScoringMethod:
        return self._scoring_method

    @property
    def is_default(self) -> bool:
        return self._is_default

    @property
    def status(self) -> StrategyStatus:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status == StrategyStatus.ACTIVE

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self) -> None:
        self._status = StrategyStatus.ACTIVE

    def deactivate(self) -> None:
        self._status = StrategyStatus.INACTIVE

    def deprecate(self) -> None:
        self._status = StrategyStatus.DEPRECATED

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":    self._strategy_id,
            "name":           self._name,
            "strategy_type":  self._strategy_type.value,
            "status":         self._status.value,
            "is_default":     self._is_default,
            "is_active":      self.is_active,
            "objective_count":  len(self._objectives),
            "constraint_count": len(self._constraints),
            "scoring_method": self._scoring_method.value,
            "framework_version": VERSION,
        }

    def __repr__(self) -> str:
        return (
            f"PortfolioOptimizationStrategy(name={self._name!r}, "
            f"type={self._strategy_type.value!r}, objectives={len(self._objectives)}, "
            f"constraints={len(self._constraints)}, is_default={self._is_default})"
        )
