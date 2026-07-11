"""iios/investment/market/sector_rotation/relative_strength_ranker.py
Ranks sectors (and industries) by relative strength.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.sector_rotation.models import (
    IndustryProfile,
    RelativeStrengthScore,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.relative_strength_score import (
    compute_rs_score,
)


def rank_sectors_by_rs(
    sector_perfs: Dict[str, SectorPerformance],
) -> Dict[str, RelativeStrengthScore]:
    """Produce RS scores for all sectors, ranked by 20-bar relative performance."""
    if not sector_perfs:
        return {}

    # Sort by 20-bar relative return to establish ranks
    ranked = sorted(
        sector_perfs.values(),
        key=lambda p: p.rel_return_20bar,
        reverse=True,
    )
    avg_rel20 = (
        sum(p.rel_return_20bar for p in sector_perfs.values()) / len(sector_perfs)
    )

    result: Dict[str, RelativeStrengthScore] = {}
    for rank_i, perf in enumerate(ranked, start=1):
        vs_group = perf.rel_return_20bar - avg_rel20
        rs = compute_rs_score(
            symbol=perf.sector,
            vs_benchmark=perf.rel_return_20bar,
            vs_group=vs_group,
            rank=rank_i,
            total=len(ranked),
        )
        result[perf.sector] = rs

    return result


def rank_industries_by_rs(
    industry_profiles: Dict[str, IndustryProfile],
    sector_rs: Dict[str, RelativeStrengthScore],
) -> Dict[str, RelativeStrengthScore]:
    """Produce RS scores for all industries."""
    if not industry_profiles:
        return {}

    # Sort within all industries by 20-bar return
    ranked = sorted(
        industry_profiles.values(),
        key=lambda p: p.return_20bar,
        reverse=True,
    )
    avg_ret20 = (
        sum(p.return_20bar for p in industry_profiles.values()) / len(industry_profiles)
    )

    result: Dict[str, RelativeStrengthScore] = {}
    for rank_i, prof in enumerate(ranked, start=1):
        vs_benchmark = prof.rel_to_benchmark
        vs_group     = prof.return_20bar - avg_ret20
        rs = compute_rs_score(
            symbol=prof.industry,
            vs_benchmark=vs_benchmark,
            vs_group=vs_group,
            rank=rank_i,
            total=len(ranked),
        )
        result[prof.industry] = rs

    return result
