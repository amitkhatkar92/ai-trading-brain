"""iios/investment/market/opportunity/ranking_engine.py
Ranks all active opportunities each bar.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from iios.investment.market.opportunity.models import (
    AssetObservation,
    IntelligenceContext,
    Opportunity,
    RankingScore,
)
from iios.investment.market.opportunity.ranking_score import score_opportunity

log = logging.getLogger(__name__)


class RankingEngine:
    """Computes and maintains composite ranking scores for all opportunities.

    Supports pluggable ranking models via ``register_model``.
    """

    def __init__(self) -> None:
        self._scores:       Dict[str, RankingScore] = {}   # opp_id → score
        self._obs_index:    Dict[str, IntelligenceContext] = {}  # symbol → ctx

    # ── update ────────────────────────────────────────────────────────────────

    def update(
        self,
        opportunities: List[Opportunity],
        observations:  List[AssetObservation],
    ) -> List[Opportunity]:
        """Score and rank all opportunities; return opportunities sorted by rank."""
        # Rebuild observation index
        self._obs_index = {obs.symbol: obs.intelligence for obs in observations}

        scores: List[RankingScore] = []
        for opp in opportunities:
            ctx = self._obs_index.get(opp.symbol)
            if ctx is None:
                ctx = IntelligenceContext()
            try:
                rs = score_opportunity(opp, ctx)
                scores.append(rs)
                self._scores[opp.opportunity_id] = rs
            except Exception:
                log.exception("Ranking error for %s", opp.symbol)

        # Sort descending by composite score
        scores.sort(key=lambda s: s.composite_score, reverse=True)

        # Assign ranks and update opportunities in-place
        opp_by_id = {o.opportunity_id: o for o in opportunities}
        for rank_i, rs in enumerate(scores, start=1):
            rs.rank = rank_i
            opp = opp_by_id.get(rs.opportunity_id)
            if opp is not None:
                opp.rank            = rank_i
                opp.composite_score = rs.composite_score
                opp.priority_score  = rs.composite_score

        return sorted(opportunities, key=lambda o: o.rank)

    # ── queries ───────────────────────────────────────────────────────────────

    def get_score(self, opportunity_id: str) -> Optional[RankingScore]:
        return self._scores.get(opportunity_id)

    def top_n(self, n: int) -> List[RankingScore]:
        ranked = sorted(
            self._scores.values(),
            key=lambda s: s.composite_score,
            reverse=True,
        )
        return ranked[:n]
