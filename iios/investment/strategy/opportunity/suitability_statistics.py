"""iios/investment/strategy/opportunity/suitability_statistics.py
Pure-function math helpers for suitability scoring.
No side effects, no state.
"""
from __future__ import annotations

import math
from typing import Dict, List


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def score_bool(condition: bool, true_score: float = 100.0, false_score: float = 0.0) -> float:
    return true_score if condition else false_score


def weighted_average(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """Compute a weighted average; handles missing weight keys gracefully."""
    total_w = 0.0
    total_s = 0.0
    for k, s in scores.items():
        w = weights.get(k, 0.0)
        total_w += w
        total_s += w * s
    return total_s / total_w if total_w > 0.0 else 0.0


def linear_scale(value: float, low: float, high: float, invert: bool = False) -> float:
    """Map value from [low, high] to [0, 100].  Clamps outside range."""
    if high <= low:
        return 100.0 if value >= high else 0.0
    raw = (value - low) / (high - low) * 100.0
    scaled = clamp(raw)
    return 100.0 - scaled if invert else scaled


def volatility_compat(
    min_vol_regime: str | None,
    max_vol_regime: str | None,
    market_vol: str,
    order: Dict[str, int] | None = None,
) -> float:
    """
    Return [0, 100] compatibility between strategy volatility tolerance
    and current market volatility regime.
    """
    _order = order or {"low": 0, "moderate": 1, "high": 2, "extreme": 3}
    mv   = _order.get(market_vol, 1)
    lo   = _order.get(min_vol_regime, 0) if min_vol_regime else 0
    hi   = _order.get(max_vol_regime, 3) if max_vol_regime else 3
    if lo <= mv <= hi:
        return 100.0
    distance = min(abs(mv - lo), abs(mv - hi))
    return clamp(100.0 - distance * 30.0)


def capital_score(required: float, available: float) -> float:
    """How well does available capital satisfy the requirement?"""
    if available <= 0.0 or required <= 0.0:
        return 0.0
    ratio = available / required
    if ratio >= 2.0:
        return 100.0
    if ratio >= 1.0:
        return 50.0 + (ratio - 1.0) * 50.0  # 50 – 100 range
    return clamp(ratio * 50.0)              # 0 – 50 range


def risk_compat(strategy_max_dd: float, opportunity_risk: float) -> float:
    """
    Compatibility between strategy's max-drawdown tolerance and the
    risk level implied by the opportunity.
    Both inputs: 0–1 (higher = riskier).
    """
    if strategy_max_dd <= 0.0:
        return 0.0
    ratio = opportunity_risk / strategy_max_dd
    if ratio <= 1.0:
        return 100.0
    return clamp(100.0 / ratio)


def timeframe_score(supported: List[str], required: str) -> float:
    if "all" in supported or required in supported:
        return 100.0
    return 0.0


def execution_readiness_score(approval_status: str, eval_score: float) -> float:
    """Combine approval status and evaluation score into a readiness score."""
    status_scores = {"approved": 100.0, "conditional": 60.0, "rejected": 0.0, "pending": 20.0}
    status_s = status_scores.get(approval_status, 0.0)
    return 0.60 * status_s + 0.40 * clamp(eval_score)
