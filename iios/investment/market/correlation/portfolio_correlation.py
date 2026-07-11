"""iios/investment/market/correlation/portfolio_correlation.py
Portfolio-level correlation metrics assuming equal-weight allocation.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.market.correlation.models import CorrelationMatrix


def equal_weight_portfolio_correlation(matrix: CorrelationMatrix) -> float:
    """
    Weighted average pairwise correlation for an equal-weight portfolio.
    = (avg_abs_pairwise_correlation) for equal weights.
    """
    syms = matrix.symbols
    n = len(syms)
    if n < 2:
        return 0.0

    total = 0.0
    count = 0
    for i, sa in enumerate(syms):
        for sb in syms[i + 1:]:
            v = matrix.get(sa, sb)
            if v is not None:
                total += v
                count += 1
    return total / max(count, 1)


def weighted_portfolio_correlation(
    matrix: CorrelationMatrix,
    weights: Dict[str, float],
) -> float:
    """
    Weighted pairwise correlation: sum_{i!=j} w_i * w_j * rho_{ij}.
    """
    syms = [s for s in matrix.symbols if s in weights]
    total_w = sum(weights.get(s, 0.0) for s in syms)
    if total_w < 1e-12:
        return 0.0

    norm = {s: weights[s] / total_w for s in syms}
    result = 0.0
    for i, sa in enumerate(syms):
        for sb in syms[i + 1:]:
            v = matrix.get(sa, sb)
            if v is not None:
                result += 2 * norm[sa] * norm[sb] * v
    return result


def portfolio_variance_contribution(
    matrix: CorrelationMatrix,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Contribution of each asset to total portfolio correlation (equal weight
    if weights not provided).
    """
    syms = matrix.symbols
    n = len(syms)
    if n == 0:
        return {}

    if weights is None:
        w = {s: 1.0 / n for s in syms}
    else:
        total = sum(weights.get(s, 0.0) for s in syms)
        w = {s: weights.get(s, 0.0) / max(total, 1e-12) for s in syms}

    contrib: Dict[str, float] = {s: 0.0 for s in syms}
    for sa in syms:
        for sb in syms:
            if sa == sb:
                continue
            v = matrix.get(sa, sb)
            if v is not None:
                contrib[sa] += w[sa] * w[sb] * v

    return contrib
