"""iios/investment/strategy/portfolio/optimization_statistics.py
Pure-function math helpers for portfolio optimization.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from iios.investment.strategy.portfolio.portfolio_statistics import (
    safe_div, herfindahl_index, effective_n
)


def portfolio_return(weights: List[float], returns: List[float]) -> float:
    """Weighted average portfolio return."""
    return sum(w * r for w, r in zip(weights, returns))


def portfolio_variance(
    weights: List[float], vols: List[float], corr: List[List[float]]
) -> float:
    """σ²_p from covariance matrix (built from vol + corr)."""
    n = len(weights)
    total = 0.0
    for i in range(n):
        for j in range(n):
            rho = (
                corr[i][j]
                if i < len(corr) and j < len(corr[i])
                else (1.0 if i == j else 0.0)
            )
            total += weights[i] * weights[j] * vols[i] * vols[j] * rho
    return max(0.0, total)


def concentration_score(weights: List[float]) -> float:
    """
    Concentration score [0, 1].
    0 = perfectly diversified, 1 = concentrated in one strategy.
    Based on Herfindahl-Hirschman Index normalised by (1/N).
    """
    n = len(weights)
    if n <= 1:
        return 1.0
    hhi  = herfindahl_index(weights)
    min_hhi = 1.0 / n       # perfectly equal weights
    return safe_div(hhi - min_hhi, 1.0 - min_hhi, 0.0)


def coverage_score(
    weights: List[float], min_w: float, max_w: float
) -> float:
    """
    How well do weights fit within [min_w, max_w]?
    1.0 = all weights within bounds, 0.0 = all violating.
    """
    if not weights:
        return 0.0
    within = sum(1 for w in weights if min_w <= w <= max_w)
    return within / len(weights)


def target_tracking_error(
    actual: Dict[str, float], target: Dict[str, float]
) -> float:
    """L2 distance between actual and target weights."""
    keys = set(actual) | set(target)
    return math.sqrt(sum((actual.get(k, 0.0) - target.get(k, 0.0)) ** 2 for k in keys))


def sortino_proxy(ann_return: float, max_drawdown: float, risk_free: float = 0.06) -> float:
    """Sortino proxy: (R-Rf) / MaxDD."""
    return safe_div(ann_return - risk_free, max(max_drawdown, 0.01), 0.0)


def blend_weights(
    ws1: Dict[str, float], ws2: Dict[str, float], alpha: float
) -> Dict[str, float]:
    """Linear blend: alpha * ws1 + (1-alpha) * ws2."""
    keys = set(ws1) | set(ws2)
    blended = {k: alpha * ws1.get(k, 0.0) + (1.0 - alpha) * ws2.get(k, 0.0) for k in keys}
    total = sum(blended.values())
    return {k: v / total for k, v in blended.items()} if total > 0 else blended
