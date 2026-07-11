"""iios/investment/market/sector_rotation/industry_engine.py
Orchestrates all industry trackers and exposes ranked industry intelligence.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from iios.investment.market.sector_rotation.industry_profile import build_industry_profiles
from iios.investment.market.sector_rotation.industry_tracker import IndustryTracker
from iios.investment.market.sector_rotation.models import (
    IndustryProfile,
    MarketSnapshot,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy

log = logging.getLogger(__name__)


class IndustryEngine:
    """Manages per-industry tracking and returns ranked profiles."""

    def __init__(self, taxonomy: SectorTaxonomy, window: int = 120) -> None:
        self._taxonomy  = taxonomy
        self._window    = window
        self._trackers: Dict[str, IndustryTracker] = {}
        self._current:  Dict[str, IndustryProfile] = {}

    # ── update ────────────────────────────────────────────────────────────────

    def update(
        self,
        snapshot: MarketSnapshot,
        sector_perfs: Dict[str, SectorPerformance],
    ) -> Dict[str, IndustryProfile]:
        self._current = build_industry_profiles(
            snapshot=snapshot,
            sector_perfs=sector_perfs,
            taxonomy=self._taxonomy,
            trackers=self._trackers,
        )
        return self._current

    # ── queries ───────────────────────────────────────────────────────────────

    def current_profiles(self) -> Dict[str, IndustryProfile]:
        return dict(self._current)

    def ranked(self, n: Optional[int] = None) -> List[IndustryProfile]:
        """Industries sorted by momentum_score descending."""
        ranked = sorted(
            self._current.values(),
            key=lambda p: p.momentum_score,
            reverse=True,
        )
        return ranked[:n] if n is not None else ranked

    def leaders(self, n: int = 5) -> List[str]:
        return [p.industry for p in self.ranked(n)]

    def laggards(self, n: int = 5) -> List[str]:
        ranked = sorted(
            self._current.values(),
            key=lambda p: p.momentum_score,
        )
        return [p.industry for p in ranked[:n]]

    def industries_in_sector(self, sector: str) -> List[IndustryProfile]:
        return [p for p in self._current.values() if p.sector == sector]

    def get(self, industry: str) -> Optional[IndustryProfile]:
        return self._current.get(industry)
