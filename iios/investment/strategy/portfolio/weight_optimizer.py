"""iios/investment/strategy/portfolio/weight_optimizer.py
WeightOptimizer — pluggable allocation algorithms.

Each algorithm is a callable: (strategies, constraints) → Dict[id, weight]
The WeightOptimizer dispatches to the appropriate algorithm based on
AllocationMethod, then projects weights onto the feasible simplex.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_allocation import AllocationMethod
from iios.investment.strategy.portfolio.construction_constraints import ConstructionConstraints
from iios.investment.strategy.portfolio.portfolio_statistics import (
    clamp, normalize_weights, project_weights
)


AllocationFn = Callable[
    [List[PortfolioStrategy], ConstructionConstraints],
    Dict[str, float],
]


def _equal_weight(
    strategies: List[PortfolioStrategy], _: ConstructionConstraints
) -> Dict[str, float]:
    n = len(strategies)
    return {s.strategy_id: 1.0 / n for s in strategies} if n else {}


def _risk_parity(
    strategies: List[PortfolioStrategy], _: ConstructionConstraints
) -> Dict[str, float]:
    """Inverse-volatility weighting (proxy: max_drawdown as vol proxy)."""
    inv_vols = {}
    for s in strategies:
        vol = max(s.annualized_vol, 0.01)
        inv_vols[s.strategy_id] = 1.0 / vol
    return normalize_weights(inv_vols)


def _performance_weight(
    strategies: List[PortfolioStrategy], _: ConstructionConstraints
) -> Dict[str, float]:
    """Weight proportional to positive Sharpe ratio."""
    raw = {}
    for s in strategies:
        raw[s.strategy_id] = max(s.sharpe_ratio, 0.0)
    return normalize_weights(raw)


def _confidence_weight(
    strategies: List[PortfolioStrategy], _: ConstructionConstraints
) -> Dict[str, float]:
    """Weight proportional to confidence score (from EvaluationEngine)."""
    raw = {s.strategy_id: max(s.confidence_score, 0.0) for s in strategies}
    return normalize_weights(raw)


def _volatility_weight(
    strategies: List[PortfolioStrategy], _: ConstructionConstraints
) -> Dict[str, float]:
    """Inverse max_drawdown weighting — lower DD gets higher weight."""
    raw = {}
    for s in strategies:
        dd = max(s.max_drawdown, 0.01)
        raw[s.strategy_id] = 1.0 / dd
    return normalize_weights(raw)


def _evaluation_weight(
    strategies: List[PortfolioStrategy], _: ConstructionConstraints
) -> Dict[str, float]:
    """Weight proportional to overall evaluation score."""
    raw = {s.strategy_id: max(s.evaluation_score, 0.0) for s in strategies}
    return normalize_weights(raw)


def _composite_weight(
    strategies: List[PortfolioStrategy], _: ConstructionConstraints
) -> Dict[str, float]:
    """
    Composite allocation: blend of performance, risk, and confidence.
    Weights: Sharpe 35%, eval_score 30%, risk_parity 20%, confidence 15%.
    """
    perf   = _performance_weight(strategies, _)
    risk   = _risk_parity(strategies, _)
    evalu  = _evaluation_weight(strategies, _)
    conf   = _confidence_weight(strategies, _)
    raw = {}
    for s in strategies:
        sid = s.strategy_id
        raw[sid] = (
            0.35 * perf.get(sid, 0.0)
            + 0.20 * risk.get(sid, 0.0)
            + 0.30 * evalu.get(sid, 0.0)
            + 0.15 * conf.get(sid, 0.0)
        )
    total = sum(raw.values())
    if total <= 0.0:
        return _equal_weight(strategies, _)
    return {k: v / total for k, v in raw.items()}


_ALGORITHM_REGISTRY: Dict[AllocationMethod, AllocationFn] = {
    AllocationMethod.EQUAL_WEIGHT:       _equal_weight,
    AllocationMethod.RISK_PARITY:        _risk_parity,
    AllocationMethod.PERFORMANCE_WEIGHT: _performance_weight,
    AllocationMethod.CONFIDENCE_WEIGHT:  _confidence_weight,
    AllocationMethod.VOLATILITY_WEIGHT:  _volatility_weight,
    AllocationMethod.EVALUATION_WEIGHT:  _evaluation_weight,
    AllocationMethod.COMPOSITE_WEIGHT:   _composite_weight,
}


class WeightOptimizer:
    """
    Dispatches to the appropriate allocation algorithm and projects
    the resulting weights onto the feasible simplex defined by constraints.

    Additional custom algorithms can be registered at runtime via
    `register_algorithm`.
    """

    def __init__(self) -> None:
        self._registry: Dict[AllocationMethod, AllocationFn] = dict(_ALGORITHM_REGISTRY)

    def register_algorithm(
        self, method: AllocationMethod, fn: AllocationFn
    ) -> None:
        """Register a custom allocation algorithm for a given method."""
        self._registry[method] = fn

    def compute(
        self,
        strategies: List[PortfolioStrategy],
        method: AllocationMethod,
        constraints: ConstructionConstraints,
    ) -> Dict[str, float]:
        """
        Compute target weights for the given strategies.
        Returns projected feasible weights summing to 1.0.
        """
        if not strategies:
            return {}

        algo = self._registry.get(method, _equal_weight)
        raw  = algo(strategies, constraints)

        return project_weights(
            raw,
            min_w=constraints.min_weight,
            max_w=constraints.max_weight,
        )
