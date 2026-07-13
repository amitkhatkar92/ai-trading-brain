"""iios/investment/strategy/risk/drawdown_statistics.py
Pure-function math helpers for drawdown analysis.
"""
from __future__ import annotations

import math
from typing import List, Optional

from iios.investment.strategy.risk.risk_statistics import clamp, safe_div


def calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
    """Calmar = Ann.Return / Max.Drawdown.  Higher is better."""
    return safe_div(annualized_return, max(max_drawdown, 0.001), 0.0)


def ulcer_index(drawdowns: List[float]) -> float:
    """
    Ulcer Index = sqrt(mean(dd^2)) where drawdowns are 0-1 fractions.
    Lower = less volatile drawdown.
    """
    if not drawdowns:
        return 0.0
    return math.sqrt(sum(d * d for d in drawdowns) / len(drawdowns))


def pain_index(drawdowns: List[float]) -> float:
    """Mean absolute drawdown (0-1 scale)."""
    if not drawdowns:
        return 0.0
    return sum(abs(d) for d in drawdowns) / len(drawdowns)


def expected_drawdown(max_drawdown: float, win_rate: float) -> float:
    """
    Expected drawdown proxy.
    ED ≈ max_drawdown × (1 - win_rate)^0.5  (empirical)
    """
    return clamp(max_drawdown * math.sqrt(1.0 - win_rate), 0.0, max_drawdown)


def max_expected_drawdown(
    annualized_vol: float,
    horizon_years: float = 1.0,
) -> float:
    """
    Expected maximum drawdown under Geometric Brownian Motion:
    E[MaxDD] ≈ σ * sqrt(T) * 0.84   (approximation)
    """
    return clamp(annualized_vol * math.sqrt(horizon_years) * 0.84, 0.0, 1.0)


def recovery_days_estimate(
    max_drawdown: float,
    annualized_return: float,
) -> float:
    """
    Approximate recovery time in trading days.
    Recovery ≈ max_drawdown / (annualized_return / 252)
    """
    daily_return = annualized_return / 252.0
    if daily_return <= 0.0:
        return float("inf")
    return max_drawdown / daily_return


def recovery_probability(
    max_drawdown: float,
    win_rate: float,
    sharpe_ratio: float,
) -> float:
    """
    Heuristic recovery probability [0, 1].
    Based on Sharpe and drawdown depth.
    """
    if max_drawdown <= 0.05:
        base = 0.90
    elif max_drawdown <= 0.15:
        base = 0.75
    elif max_drawdown <= 0.25:
        base = 0.55
    elif max_drawdown <= 0.40:
        base = 0.35
    else:
        base = 0.20

    # Sharpe and win-rate adjustment
    quality_bonus = min(0.15, max(0.0, (sharpe_ratio - 0.5) * 0.10 + (win_rate - 0.5) * 0.10))
    return clamp(base + quality_bonus, 0.0, 1.0)


def drawdown_risk_score(max_drawdown: float, expected_dd: float) -> float:
    """Composite drawdown risk score (0-100)."""
    depth_score  = clamp(max_drawdown / 0.40 * 100.0)
    expect_score = clamp(expected_dd / 0.25 * 100.0)
    return clamp(0.60 * depth_score + 0.40 * expect_score)
