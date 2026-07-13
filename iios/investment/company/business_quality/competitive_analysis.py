"""iios/investment/company/business_quality/competitive_analysis.py
Orchestrates market position, peer comparison, and industry structure
into CompetitiveIntelligenceProfile.
"""
from __future__ import annotations

from typing import Any, List

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.competitive_position import (
    CompetitiveIntelligenceProfile,
)
from iios.investment.company.business_quality.market_position import MarketPositionAnalyzer
from iios.investment.company.business_quality.peer_comparison import PeerComparisonAnalyzer
from iios.investment.company.business_quality.industry_structure import IndustryStructureAnalyzer
from iios.investment.company.business_quality.quality_statistics import clamp


class CompetitiveAnalyzer:
    """Produces CompetitiveIntelligenceProfile from context + optional peers."""

    def __init__(self) -> None:
        self._market_pos   = MarketPositionAnalyzer()
        self._peer_cmp     = PeerComparisonAnalyzer()
        self._industry_str = IndustryStructureAnalyzer()

    def analyze(
        self,
        ctx:           AssessmentContext,
        own_snapshot:  Any = None,
        peers:         List[Any] = None,
    ) -> CompetitiveIntelligenceProfile:
        profile = CompetitiveIntelligenceProfile()

        peers = peers or []

        # ── Market position ────────────────────────────────────────────────────
        profile.market_position = self._market_pos.analyze(ctx)

        # ── Peer comparison ────────────────────────────────────────────────────
        if own_snapshot is not None and peers:
            profile.peer_comparison = self._peer_cmp.analyze(
                ticker=ctx.ticker,
                own_snapshot=own_snapshot,
                peer_snapshots=peers,
            )
        else:
            # No peer data: score is neutral (50)
            profile.peer_comparison.competitive_score_vs_peers = 50.0

        # ── Composite competitive score ────────────────────────────────────────
        mp_score   = profile.market_position.market_position_score
        peer_score = profile.peer_comparison.competitive_score_vs_peers

        # Weight peer comparison more if we have data
        if peers:
            composite = mp_score * 0.50 + peer_score * 0.50
        else:
            composite = mp_score

        profile.competitive_intelligence_score = clamp(composite)

        return profile

    def score(self, profile: CompetitiveIntelligenceProfile) -> float:
        return profile.competitive_intelligence_score
