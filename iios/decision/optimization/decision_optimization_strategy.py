"""
decision_optimization_strategy.py — iios.decision.optimization
================================================================
DecisionOptimizationStrategy — a named, configurable optimization strategy.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .constants import OptimizationStrategyType


@dataclass
class DecisionOptimizationStrategy:
    """
    A named optimization strategy that governs how the best candidate
    is selected from a scored and ranked set.

    The strategy type determines the selection algorithm used by
    :class:`DecisionSolutionSelector`.  For ``CUSTOM`` strategies, a
    callable may be provided via ``_custom_callable``.

    Parameters
    ----------
    strategy_id :   Unique identifier.
    name :          Human-readable name.
    strategy_type : Algorithm to apply (weighted score, pareto, etc.).
    config :        Strategy-specific configuration parameters.
    description :   Optional explanation.
    """

    strategy_id:    str
    name:           str
    strategy_type:  OptimizationStrategyType
    config:         Dict[str, Any]              = field(default_factory=dict)
    description:    str                         = ""
    _custom_callable: Optional[Callable]        = field(
        default=None, repr=False, compare=False
    )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:            str,
        strategy_type:   OptimizationStrategyType,
        *,
        strategy_id:     Optional[str]      = None,
        config:          Optional[Dict]      = None,
        description:     str                = "",
        custom_callable: Optional[Callable] = None,
    ) -> "DecisionOptimizationStrategy":
        return cls(
            strategy_id      = strategy_id or str(uuid.uuid4()),
            name             = name,
            strategy_type    = strategy_type,
            config           = config or {},
            description      = description,
            _custom_callable = custom_callable,
        )

    # ------------------------------------------------------------------
    # Default built-in strategies (factory helpers)
    # ------------------------------------------------------------------

    @classmethod
    def weighted_score(cls, *, strategy_id: Optional[str] = None) -> "DecisionOptimizationStrategy":
        """Create the default WEIGHTED_SCORE strategy."""
        return cls.create(
            "Weighted Score",
            OptimizationStrategyType.WEIGHTED_SCORE,
            strategy_id = strategy_id,
            description = "Select the candidate with the highest weighted objective score.",
        )

    @classmethod
    def priority_based(cls, *, strategy_id: Optional[str] = None) -> "DecisionOptimizationStrategy":
        return cls.create(
            "Priority Based",
            OptimizationStrategyType.PRIORITY_BASED,
            strategy_id = strategy_id,
            description = "Select the candidate with the highest confidence × expected_return.",
        )

    @classmethod
    def pareto_ranking(cls, *, strategy_id: Optional[str] = None) -> "DecisionOptimizationStrategy":
        return cls.create(
            "Pareto Ranking",
            OptimizationStrategyType.PARETO_RANKING,
            strategy_id = strategy_id,
            description = "Select the non-dominated (Pareto-optimal) candidate with the best weighted score.",
        )
