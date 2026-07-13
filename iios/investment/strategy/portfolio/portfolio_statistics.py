"""iios/investment/strategy/portfolio/portfolio_statistics.py
Pure-function math helpers for portfolio construction and scoring.
No side effects, no state.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def safe_div(num: float, denom: float, default: float = 0.0) -> float:
    return num / denom if abs(denom) > 1e-12 else default


def normalize_weights(raw: Dict[str, float], min_w: float = 0.0) -> Dict[str, float]:
    """Normalise raw scores to sum to 1.0, applying a floor of min_w."""
    total = sum(max(v, min_w) for v in raw.values())
    if total <= 0.0:
        n = max(len(raw), 1)
        return {k: 1.0 / n for k in raw}
    return {k: max(v, min_w) / total for k, v in raw.items()}


def project_weights(
    weights: Dict[str, float],
    min_w: float = 0.02,
    max_w: float = 0.50,
    max_iter: int = 50,
) -> Dict[str, float]:
    """
    Project weights onto the feasible simplex:
      - each weight in [min_w, max_w]
      - sum = 1.0
    Uses iterative clamp-and-renormalize.
    """
    w = dict(weights)
    n = len(w)
    if n == 0:
        return {}
    # Ensure min_w * n <= 1.0 <= max_w * n
    min_w = min(min_w, 1.0 / n)
    max_w = max(max_w, 1.0 / n)

    for _ in range(max_iter):
        # Clamp
        clamped = {k: clamp(v, min_w, max_w) for k, v in w.items()}
        total = sum(clamped.values())
        if abs(total - 1.0) < 1e-9:
            return clamped
        # Renormalize
        excess = total - 1.0
        free_mass = sum(
            v for v in clamped.values()
            if (v > min_w + 1e-9 and excess > 0) or (v < max_w - 1e-9 and excess < 0)
        )
        if free_mass < 1e-9:
            break
        adj = excess / free_mass
        w = {}
        for k, v in clamped.items():
            can_adjust = (excess > 0 and v > min_w + 1e-9) or (excess < 0 and v < max_w - 1e-9)
            w[k] = clamp(v - adj * v, min_w, max_w) if can_adjust else v
    # Final renormalize
    total = sum(w.values())
    return {k: v / total for k, v in w.items()} if total > 0 else {k: 1.0 / n for k in w}


def jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    """Jaccard similarity between two tag/sector/timeframe lists."""
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union > 0 else 0.0


def portfolio_variance(
    weights: List[float], vols: List[float], correlations: List[List[float]]
) -> float:
    """σ²_p = Σ_i Σ_j w_i * w_j * σ_i * σ_j * ρ_ij"""
    n = len(weights)
    total = 0.0
    for i in range(n):
        for j in range(n):
            rho = correlations[i][j] if i < len(correlations) and j < len(correlations[i]) else (1.0 if i == j else 0.0)
            total += weights[i] * weights[j] * vols[i] * vols[j] * rho
    return max(0.0, total)


def herfindahl_index(weights: List[float]) -> float:
    """HHI = Σ w_i²; 1/N = perfect diversification, 1.0 = full concentration."""
    return sum(w * w for w in weights)


def effective_n(weights: List[float]) -> float:
    """1 / HHI; = N for equal weights."""
    hhi = herfindahl_index(weights)
    return safe_div(1.0, hhi, default=1.0)


def diversification_ratio(
    weights: List[float], vols: List[float], portfolio_vol: float
) -> float:
    """DR = Σ(w_i * σ_i) / σ_p; DR > 1 means diversification benefit."""
    weighted_vol_sum = sum(w * s for w, s in zip(weights, vols))
    return safe_div(weighted_vol_sum, portfolio_vol, default=1.0)


def annualized_sharpe(
    ann_return: float, ann_vol: float, risk_free: float = 0.06
) -> float:
    if ann_vol <= 0.0:
        return 0.0
    return (ann_return - risk_free) / ann_vol


def weighted_average(values: List[float], weights: List[float]) -> float:
    total_w = sum(weights)
    if total_w <= 0.0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_w


def gini_coefficient(values: List[float]) -> float:
    """Gini coefficient of weight inequality. 0 = equal, 1 = maximally unequal."""
    n = len(values)
    if n <= 1:
        return 0.0
    s = sorted(values)
    cum = 0.0
    for i, v in enumerate(s):
        cum += (2 * (i + 1) - n - 1) * v
    return safe_div(cum, n * sum(s), 0.0)
