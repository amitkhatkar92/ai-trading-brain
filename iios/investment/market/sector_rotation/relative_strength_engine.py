"""iios/investment/market/sector_rotation/relative_strength_engine.py
Orchestrator for sector and industry relative-strength computation.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.market.sector_rotation.models import (
    IndustryProfile,
    RelativeStrengthScore,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.relative_strength_ranker import (
    rank_industries_by_rs,
    rank_sectors_by_rs,
)


class RelativeStrengthEngine:
    """Computes and caches RS scores for sectors and industries."""

    def __init__(self) -> None:
        self._sector_rs:   Dict[str, RelativeStrengthScore] = {}
        self._industry_rs: Dict[str, RelativeStrengthScore] = {}

    def update(
        self,
        sector_perfs: Dict[str, SectorPerformance],
        industry_profiles: Dict[str, IndustryProfile],
    ) -> None:
        self._sector_rs   = rank_sectors_by_rs(sector_perfs)
        self._industry_rs = rank_industries_by_rs(industry_profiles, self._sector_rs)

    # ── queries ───────────────────────────────────────────────────────────────

    def sector_rs(self) -> Dict[str, RelativeStrengthScore]:
        return dict(self._sector_rs)

    def industry_rs(self) -> Dict[str, RelativeStrengthScore]:
        return dict(self._industry_rs)

    def get_sector(self, sector: str) -> Optional[RelativeStrengthScore]:
        return self._sector_rs.get(sector)

    def get_industry(self, industry: str) -> Optional[RelativeStrengthScore]:
        return self._industry_rs.get(industry)

    def sector_leaders(self, n: int = 3) -> List[str]:
        ranked = sorted(
            self._sector_rs.values(),
            key=lambda r: r.composite,
            reverse=True,
        )
        return [r.symbol for r in ranked[:n]]

    def sector_laggards(self, n: int = 3) -> List[str]:
        ranked = sorted(
            self._sector_rs.values(),
            key=lambda r: r.composite,
        )
        return [r.symbol for r in ranked[:n]]

    def industry_leaders(self, n: int = 5) -> List[str]:
        ranked = sorted(
            self._industry_rs.values(),
            key=lambda r: r.composite,
            reverse=True,
        )
        return [r.symbol for r in ranked[:n]]
