"""
market_rotation_engine.py — iios.market.analytics
==================================================
Sector rotation detection sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import RotationResult, SectorResult


class MarketRotationEngine:
    """
    Stateless sector rotation sub-engine.

    Accepts already-computed :class:`~.market_analytics_response.SectorResult`
    list and identifies leading vs lagging sectors.
    """

    _N_LEADERS  = 3
    _N_LAGGERS  = 3

    def run(
        self,
        context:        MarketAnalyticsContext,
        sector_results: List[SectorResult],
    ) -> Optional[RotationResult]:
        if not sector_results:
            return None

        # Already ranked descending by performance from MarketSectorEngine
        n_leaders = min(self._N_LEADERS, len(sector_results))
        n_laggers = min(self._N_LAGGERS, len(sector_results))

        leading = tuple(s.sector_name for s in sector_results[:n_leaders])
        lagging = tuple(s.sector_name for s in sector_results[-n_laggers:])

        rotation_score = self._rotation_score(sector_results)
        phase          = self._rotation_phase(sector_results)

        return RotationResult(
            leading_sectors = leading,
            lagging_sectors = lagging,
            rotation_score  = rotation_score,
            rotation_phase  = phase,
            description     = f"Rotation: {phase}, score={rotation_score:.1f}",
        )

    @staticmethod
    def _rotation_score(sectors: List[SectorResult]) -> float:
        if not sectors:
            return 0.0
        perfs = [s.performance for s in sectors]
        if len(perfs) < 2:
            return 0.0
        spread = max(perfs) - min(perfs)
        return min(100.0, spread * 1000.0)

    @staticmethod
    def _rotation_phase(sectors: List[SectorResult]) -> str:
        if not sectors:
            return "unknown"
        leading_names = {s.sector_name.lower() for s in sectors[:3]}
        if any(n in leading_names for n in ("technology", "consumer discretionary", "communication")):
            return "early_bull"
        if any(n in leading_names for n in ("energy", "materials", "industrials")):
            return "late_bull"
        if any(n in leading_names for n in ("utilities", "consumer staples", "healthcare")):
            return "defensive"
        if any(n in leading_names for n in ("financials",)):
            return "recovery"
        return "mixed"
