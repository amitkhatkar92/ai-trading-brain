"""iios/investment/market/sector_rotation/sector_performance.py
Stateless sector performance computation functions.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Sequence

from iios.investment.market.sector_rotation.models import (
    SecurityData,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy

_EPSILON = 1e-9


def _weighted_avg_return(securities: List[SecurityData]) -> float:
    """Market-cap-weighted average return; falls back to equal-weight."""
    total_cap = sum(s.market_cap for s in securities)
    if total_cap < _EPSILON:
        n = len(securities)
        return sum(s.return_pct for s in securities) / n if n else 0.0
    return sum(s.return_pct * s.market_cap for s in securities) / total_cap


def _rolling_return(history: Sequence[float], window: int) -> float:
    """Compound of last ``window`` single-bar returns (arithmetic sum, not log)."""
    if not history:
        return 0.0
    tail = list(history)[-window:]
    return sum(tail)


def _breadth(securities: List[SecurityData]) -> float:
    if not securities:
        return 0.5
    advancing = sum(1 for s in securities if s.is_advancing)
    return advancing / len(securities)


def _avg_volume_ratio(securities: List[SecurityData]) -> float:
    ratios = [s.volume_ratio for s in securities]
    if not ratios:
        return 1.0
    return sum(ratios) / len(ratios)


def _momentum_score(
    rel_return_1: float,
    rel_return_5: float,
    rel_return_20: float,
) -> float:
    """0-100 momentum score from multi-period relative returns."""
    # Weighted blend: shorter periods count more for responsiveness
    weighted = (0.5 * rel_return_1 + 0.3 * rel_return_5 + 0.2 * rel_return_20)
    # Sigmoid-style normalisation into [0, 100]: 5% spread maps to ~50 points
    clipped = max(-0.10, min(0.10, weighted))
    return 50.0 + clipped * 500.0


def _strength_score(
    momentum: float,
    breadth: float,
    volume_ratio: float,
) -> float:
    """0-100 composite strength = momentum + breadth + volume confirmation."""
    breadth_score  = breadth * 100.0
    volume_score   = min(100.0, (volume_ratio - 1.0) * 25.0 + 50.0)
    volume_score   = max(0.0, volume_score)
    return momentum * 0.5 + breadth_score * 0.3 + volume_score * 0.2


def compute_sector_performance(
    sector: str,
    securities: List[SecurityData],
    benchmark_return: float,
    bar_index: int,
    return_history: "deque[float]",   # history of this sector's 1-bar returns
    taxonomy: SectorTaxonomy,
) -> SectorPerformance:
    """Compute a complete :class:`SectorPerformance` from current observations."""
    if not securities:
        return SectorPerformance(
            sector=sector,
            bar_index=bar_index,
            return_1bar=0.0, return_5bar=0.0, return_20bar=0.0, return_60bar=0.0,
            rel_return_1bar=0.0, rel_return_5bar=0.0, rel_return_20bar=0.0,
            breadth_pct=0.5, avg_volume_ratio=1.0,
            momentum_score=50.0, strength_score=50.0,
            n_securities=0,
            sector_character=taxonomy.character(sector),
        )

    r1   = _weighted_avg_return(securities)
    r5   = _rolling_return(return_history, 5)
    r20  = _rolling_return(return_history, 20)
    r60  = _rolling_return(return_history, 60)

    rel1  = r1  - benchmark_return
    # Approximate multi-bar relative: assume benchmark scaled proportionally
    rel5  = r5  - benchmark_return * 5
    rel20 = r20 - benchmark_return * 20

    breadth     = _breadth(securities)
    vol_ratio   = _avg_volume_ratio(securities)
    mom_score   = _momentum_score(rel1, rel5, rel20)
    str_score   = _strength_score(mom_score, breadth, vol_ratio)

    return SectorPerformance(
        sector=sector,
        bar_index=bar_index,
        return_1bar=r1,
        return_5bar=r5,
        return_20bar=r20,
        return_60bar=r60,
        rel_return_1bar=rel1,
        rel_return_5bar=rel5,
        rel_return_20bar=rel20,
        breadth_pct=breadth,
        avg_volume_ratio=vol_ratio,
        momentum_score=mom_score,
        strength_score=str_score,
        n_securities=len(securities),
        sector_character=taxonomy.character(sector),
    )
