"""
market_strength_engine.py — iios.market.analytics
===================================================
Market strength composite score sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import BreadthResult, RegimeResult


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def compute_market_strength_score(
    regime:     Optional[RegimeResult],
    breadth:    Optional[BreadthResult],
    vol_score:  float = 75.0,
    mom_score:  float = 50.0,
) -> float:
    """
    Returns a composite market strength score in [0, 100].

    Component weights:
    - Regime confidence    30 %
    - Breadth score        25 %
    - Volatility score     25 %
    - Momentum score       20 %
    """
    from .constants import REGIME_BASE_SCORES

    regime_score = 50.0
    if regime is not None:
        base        = REGIME_BASE_SCORES.get(regime.regime, 50.0)
        regime_score = base * regime.confidence + 50.0 * (1.0 - regime.confidence)

    breadth_score = breadth.breadth_score if breadth is not None else 50.0

    composite = (
        regime_score  * 0.30 +
        breadth_score * 0.25 +
        vol_score     * 0.25 +
        mom_score     * 0.20
    )
    return _clamp(composite)
