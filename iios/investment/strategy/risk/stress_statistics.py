"""iios/investment/strategy/risk/stress_statistics.py
Pure-function math for stress testing calculations.
"""
from __future__ import annotations

import math
from typing import List

from iios.investment.strategy.risk.risk_statistics import clamp, safe_div


def stressed_vol(base_vol: float, vol_multiplier: float) -> float:
    return clamp(base_vol * vol_multiplier, 0.0, 2.0)   # cap at 200%


def stressed_drawdown(base_dd: float, dd_multiplier: float) -> float:
    return clamp(base_dd * dd_multiplier, 0.0, 1.0)


def stressed_expected_loss(base_vol: float, vol_multiplier: float) -> float:
    """95% VaR under stressed vol (daily)."""
    s_vol = stressed_vol(base_vol, vol_multiplier)
    daily_s = s_vol / math.sqrt(252.0)
    # Z_95 = 1.645
    return clamp(1.645 * daily_s, 0.0, 1.0)


def risk_amplification(
    base_risk_score: float, stressed_risk_score: float
) -> float:
    """How much did risk amplify? >1 = riskier under stress."""
    return safe_div(stressed_risk_score, max(base_risk_score, 1.0), 1.0)


def survival_probability(
    base_risk_score: float, scenario_multiplier: float
) -> float:
    """
    Probability the strategy survives (does not breach limits) under the scenario.
    Heuristic: P(survive) = 1 - sigmoid((stressed_score - 60) / 20)
    """
    stressed = clamp(base_risk_score * scenario_multiplier)
    # Logistic
    x = (stressed - 60.0) / 20.0
    p = 1.0 / (1.0 + math.exp(x))
    return clamp(p, 0.0, 1.0)


def aggregate_stress_score(
    scenario_scores: List[float],
    weights: List[float],
) -> float:
    """Weighted average of per-scenario stressed risk scores."""
    if not scenario_scores:
        return 0.0
    total_w = sum(weights)
    if total_w <= 0.0:
        return sum(scenario_scores) / len(scenario_scores)
    return clamp(sum(s * w for s, w in zip(scenario_scores, weights)) / total_w)


def worst_case_loss(
    max_drawdown: float,
    dd_multiplier: float,
    portfolio_weight: float = 1.0,
) -> float:
    """Worst-case portfolio loss contribution from this strategy."""
    stressed_dd = stressed_drawdown(max_drawdown, dd_multiplier)
    return clamp(stressed_dd * portfolio_weight, 0.0, 1.0)
