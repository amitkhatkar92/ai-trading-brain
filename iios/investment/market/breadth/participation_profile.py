"""iios/investment/market/breadth/participation_profile.py
Stateless builder for ParticipationSnapshot from a UniverseSnapshot.
"""
from __future__ import annotations

from iios.investment.market.breadth.models import (
    MarketCapTier,
    ParticipationSnapshot,
    UniverseSnapshot,
)
from iios.investment.market.breadth import participation_score as ps


class ParticipationProfileBuilder:
    """Extracts cross-sectional participation data from a UniverseSnapshot."""

    def build(self, universe: UniverseSnapshot) -> ParticipationSnapshot:
        obs = universe.observations
        n = len(obs)

        # Cap tier participation
        large_pct = ps.cap_tier_pct(obs, MarketCapTier.LARGE.value)
        mid_pct   = ps.cap_tier_pct(obs, MarketCapTier.MID.value)
        small_pct = ps.cap_tier_pct(obs, MarketCapTier.SMALL.value)

        # Sector participation
        sector_map = ps.sector_participation_map(obs)
        part_breadth = ps.participation_breadth(sector_map)

        # MA data
        above_ma20 = sum(1 for o in obs if o.is_above_ma20) / max(n, 1)
        above_ma50 = sum(1 for o in obs if o.is_above_ma50) / max(n, 1)

        # New high/low
        new_highs = sum(1 for o in obs if o.is_new_52w_high)
        new_lows  = sum(1 for o in obs if o.is_new_52w_low)
        nh_nl_ratio = new_highs / max(new_lows, 1)

        # Breadth pct for overall score
        breadth_pct = sum(1 for o in obs if o.is_advancing) / max(n, 1)
        score = ps.market_participation_score(
            breadth_pct, above_ma20, above_ma50, nh_nl_ratio, part_breadth
        )

        return ParticipationSnapshot(
            large_cap_pct=large_pct,
            mid_cap_pct=mid_pct,
            small_cap_pct=small_pct,
            sector_participation=sector_map,
            above_ma20_pct=above_ma20,
            above_ma50_pct=above_ma50,
            new_highs=new_highs,
            new_lows=new_lows,
            nh_nl_ratio=nh_nl_ratio,
            market_participation_score=score,
            participation_breadth=part_breadth,
        )
