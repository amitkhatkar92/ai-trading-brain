"""iios/investment/market/breadth/participation_score.py
Stateless scoring functions for market participation.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.breadth.models import SecurityObservation


def cap_tier_pct(observations: List[SecurityObservation], tier: str) -> float:
    """Fraction of securities in *tier* that are advancing."""
    tier_obs = [o for o in observations if o.market_cap_tier == tier]
    if not tier_obs:
        return 0.5   # neutral when no data
    return sum(1 for o in tier_obs if o.is_advancing) / len(tier_obs)


def sector_participation_map(
    observations: List[SecurityObservation],
) -> Dict[str, float]:
    """Per-sector fraction of advancing securities."""
    by_sector: Dict[str, List[SecurityObservation]] = {}
    for obs in observations:
        by_sector.setdefault(obs.sector, []).append(obs)
    return {
        sector: sum(1 for o in obs_list if o.is_advancing) / len(obs_list)
        for sector, obs_list in by_sector.items()
    }


def participation_breadth(sector_map: Dict[str, float]) -> float:
    """Fraction of sectors where > 50% of securities are advancing."""
    if not sector_map:
        return 0.0
    sectors_advancing = sum(1 for v in sector_map.values() if v > 0.50)
    return sectors_advancing / len(sector_map)


def market_participation_score(
    breadth_pct: float,
    above_ma20_pct: float,
    above_ma50_pct: float,
    nh_nl_ratio: float,
    participation_breadth_val: float,
) -> float:
    """
    0-100 composite participation score.

    Weights:
      breadth_pct          0.30
      above_ma20_pct       0.25
      above_ma50_pct       0.20
      nh_nl_normalized     0.10
      part_breadth         0.15
    """
    nh_nl_norm = nh_nl_ratio / (1.0 + nh_nl_ratio)
    score = (
        breadth_pct             * 0.30
        + above_ma20_pct        * 0.25
        + above_ma50_pct        * 0.20
        + nh_nl_norm            * 0.10
        + participation_breadth_val * 0.15
    )
    return round(max(0.0, min(100.0, score * 100)), 2)
