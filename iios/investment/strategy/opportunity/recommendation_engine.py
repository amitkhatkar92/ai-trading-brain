"""iios/investment/strategy/opportunity/recommendation_engine.py
RecommendationEngine — orchestrates evidence collection and reason
generation to produce auditable RecommendationSummary objects.
"""
from __future__ import annotations

import logging
import uuid
from typing import List, Union

from iios.investment.strategy.opportunity.market_opportunity import MarketOpportunity
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.strategy_matcher import MatchResult
from iios.investment.strategy.opportunity.strategy_suitability import SuitabilityResult
from iios.investment.strategy.opportunity.ranking_score import RankingScore
from iios.investment.strategy.opportunity.evidence_collector import EvidenceCollector
from iios.investment.strategy.opportunity.reason_generator import ReasonGenerator
from iios.investment.strategy.opportunity.recommendation_summary import RecommendationSummary

logger = logging.getLogger(__name__)


def _opp_type(opp: Union[MarketOpportunity, CompanyOpportunity]) -> str:
    if isinstance(opp, MarketOpportunity):
        return opp.opportunity_type.value
    return opp.opportunity_type


class RecommendationEngine:
    """
    Produces RecommendationSummary objects from upstream engine outputs.
    Does no independent analysis — all intelligence is consumed, not generated.
    Thread-safe and stateless; safe to share across threads.
    """

    def __init__(self) -> None:
        self._collector = EvidenceCollector()
        self._reasons   = ReasonGenerator()

    def generate(
        self,
        candidate: StrategyCandidate,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
        match: MatchResult,
        suitability: SuitabilityResult,
        ranking: RankingScore,
        overall_score: float,
    ) -> RecommendationSummary:
        """
        Build a full RecommendationSummary from upstream results.
        All inputs are provided by calling engines — no analysis here.
        """
        bundle    = self._collector.collect(candidate, opportunity, match, suitability, ranking)
        opp_type  = _opp_type(opportunity)
        headline  = self._reasons.generate_headline(candidate.strategy_name, opp_type, ranking.rank)
        why       = self._reasons.why_selected(bundle)
        caution   = self._reasons.why_caution(bundle)
        neutral   = self._reasons.neutral_observations(bundle)
        conf_exp  = self._reasons.confidence_explanation(bundle)

        # Best conditions from strategy profile
        best_regimes    = list(candidate.supported_regimes)[:4]
        best_timeframes = list(candidate.supported_timeframes)[:4]
        expected_risks  = self._build_risks(candidate, suitability)

        rec_id = str(uuid.uuid4())
        logger.debug(
            "Recommendation %s: %s for %s (score=%.1f rank=%d)",
            rec_id, candidate.strategy_name, opportunity.opportunity_id,
            overall_score, ranking.rank,
        )
        return RecommendationSummary(
            recommendation_id=rec_id,
            strategy_id=candidate.strategy_id,
            strategy_name=candidate.strategy_name,
            opportunity_id=opportunity.opportunity_id,
            opportunity_type=opp_type,
            overall_score=overall_score,
            matching_score=match.score,
            suitability_score=suitability.score,
            ranking_score=ranking.overall_score,
            rank=ranking.rank,
            headline=headline,
            why_selected=why,
            caution_factors=caution,
            neutral_observations=neutral,
            confidence_explanation=conf_exp,
            net_confidence=bundle.net_confidence,
            best_regimes=best_regimes,
            best_timeframes=best_timeframes,
            expected_risks=expected_risks,
            evidence=bundle,
        )

    def _build_risks(
        self,
        c: StrategyCandidate,
        suit: SuitabilityResult,
    ) -> List[str]:
        risks: List[str] = []
        if c.max_drawdown > 0.15:
            risks.append(f"Max historical drawdown {c.max_drawdown:.0%} — monitor position sizing")
        if suit.compatibility.risk_compatibility < 60.0:
            risks.append("Risk compatibility below threshold — reduce exposure")
        if c.approval_status == "conditional":
            risks.append("Strategy is conditionally approved — additional oversight required")
        if c.robustness_score < 0.50:
            risks.append("Low robustness — performance may degrade out-of-sample")
        if not risks:
            risks.append("Standard market risk applies — follow risk management guidelines")
        return risks
