"""iios/investment/market/correlation/hedging_analysis.py
Hedging effectiveness analysis: identifies asset pairs suitable for hedging.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from iios.investment.market.correlation.models import CorrelationMatrix


_HEDGE_THRESHOLD  = -0.40   # correlation below this → useful hedge
_STRONG_HEDGE     = -0.70   # strong inverse relationship


def find_hedging_pairs(
    matrix: CorrelationMatrix,
    threshold: float = _HEDGE_THRESHOLD,
) -> List[Tuple[str, str, float]]:
    """
    Return pairs where correlation <= threshold (potential hedges).
    Sorted from most negative (best hedge) to least negative.
    """
    return matrix.inversely_correlated_pairs(threshold=threshold)


def hedge_ratio(
    asset_corr: float,
    asset_vol: float,
    hedge_vol: float,
) -> float:
    """
    Minimum variance hedge ratio: h = -rho * sigma_asset / sigma_hedge.
    Returns the fraction of the hedge position relative to the asset.
    """
    if hedge_vol < 1e-12:
        return 0.0
    return -asset_corr * asset_vol / hedge_vol


def hedging_effectiveness(
    asset_corr: float,
) -> float:
    """
    1 - (1 - rho²): fraction of variance eliminated by the hedge.
    Returns 0-1; 1 = perfect hedge.
    """
    return max(0.0, min(1.0, asset_corr ** 2))


def best_hedge_for_asset(
    symbol: str,
    matrix: CorrelationMatrix,
    threshold: float = _HEDGE_THRESHOLD,
) -> Optional[Tuple[str, float]]:
    """
    Find the best (most inverse) hedging instrument for `symbol`.
    Returns (hedge_symbol, correlation) or None.
    """
    best: Optional[Tuple[str, float]] = None
    for sym in matrix.symbols:
        if sym == symbol:
            continue
        corr = matrix.get(symbol, sym)
        if corr is None or corr > threshold:
            continue
        if best is None or corr < best[1]:
            best = (sym, corr)
    return best
