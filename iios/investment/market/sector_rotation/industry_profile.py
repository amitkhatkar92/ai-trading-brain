"""iios/investment/market/sector_rotation/industry_profile.py
Builds IndustryProfile objects from observations (thin convenience wrapper).
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.sector_rotation.models import (
    IndustryProfile,
    MarketSnapshot,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy


def build_industry_profiles(
    snapshot: MarketSnapshot,
    sector_perfs: Dict[str, SectorPerformance],
    taxonomy: SectorTaxonomy,
    trackers: Dict[str, "IndustryTracker"],  # noqa: F821  (forward ref string)
) -> Dict[str, IndustryProfile]:
    """Update all industry trackers and return current profiles."""
    from iios.investment.market.sector_rotation.industry_tracker import IndustryTracker

    by_industry = snapshot.by_industry()
    result: Dict[str, IndustryProfile] = {}

    for industry, securities in by_industry.items():
        parent_sector  = taxonomy.sector_for_industry(industry) or (
            securities[0].sector if securities else "Unknown"
        )
        sector_r1 = sector_perfs.get(parent_sector, None)
        sector_return = sector_r1.return_1bar if sector_r1 else snapshot.benchmark_return

        if industry not in trackers:
            trackers[industry] = IndustryTracker(
                industry=industry,
                parent_sector=parent_sector,
            )
        profile = trackers[industry].update(
            securities=securities,
            benchmark_return=snapshot.benchmark_return,
            sector_return_1bar=sector_return,
            bar_index=snapshot.bar_index,
        )
        result[industry] = profile

    return result
