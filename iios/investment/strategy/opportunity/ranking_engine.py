"""iios/investment/strategy/opportunity/ranking_engine.py
RankingEngine — computes RankingScore for strategy opportunities and
returns an ordered list of the best matches.

Weights (configurable):
  strategy_score    25%   – quality of the strategy itself (EvaluationEngine)
  opportunity_score 25%   – matching + suitability combined
  risk_score        20%   – risk-adjusted desirability
  robustness_score  15%   – strategy robustness
  confidence_score  10%   – data confidence
  historical_score   5%   – historical match success rate
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Union

from iios.investment.strategy.opportunity.strategy_opportunity import StrategyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.strategy_matcher import MatchResult
from iios.investment.strategy.opportunity.strategy_suitability import SuitabilityResult
from iios.investment.strategy.opportunity.ranking_score import RankingScore
from iios.investment.strategy.opportunity.suitability_statistics import clamp

logger = logging.getLogger(__name__)

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "strategy_score":    0.25,
    "opportunity_score": 0.25,
    "risk_score":        0.20,
    "robustness_score":  0.15,
    "confidence_score":  0.10,
    "historical_score":  0.05,
}


class RankingEngine:
    """
    Deterministic ranking of strategy–opportunity pairs.
    All inputs come from upstream engines — no independent analysis.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        raw = weights or _DEFAULT_WEIGHTS
        total = sum(raw.values()) or 1.0
        self._w = {k: v / total for k, v in raw.items()}

    def score(
        self,
        candidate: StrategyCandidate,
        match_result: MatchResult,
        suitability: SuitabilityResult,
        historical_pass_rate: float = 0.5,
    ) -> RankingScore:
        """Compute a RankingScore for a single candidate × opportunity pair."""

        # Strategy quality (from evaluation)
        strat_s = clamp(candidate.evaluation_score)

        # Opportunity alignment (blend matching + suitability)
        opp_s = clamp(
            match_result.score * 0.50 + suitability.score * 0.50
        )

        # Risk score — prefer lower drawdown, higher sharpe, within suitability
        risk_s = self._risk_score(candidate, suitability)

        # Robustness
        rob_s = clamp(candidate.robustness_score * 100.0)

        # Confidence
        conf_s = clamp(candidate.confidence_score)

        # Historical success
        hist_s = clamp(historical_pass_rate * 100.0)

        overall = (
            self._w["strategy_score"]    * strat_s
            + self._w["opportunity_score"] * opp_s
            + self._w["risk_score"]        * risk_s
            + self._w["robustness_score"]  * rob_s
            + self._w["confidence_score"]  * conf_s
            + self._w["historical_score"]  * hist_s
        )

        return RankingScore(
            strategy_id=candidate.strategy_id,
            opportunity_id=match_result.opportunity_id,
            strategy_score=round(strat_s, 2),
            opportunity_score=round(opp_s, 2),
            risk_score=round(risk_s, 2),
            robustness_score=round(rob_s, 2),
            confidence_score=round(conf_s, 2),
            historical_score=round(hist_s, 2),
            overall_score=round(clamp(overall), 2),
        )

    def rank(self, scores: List[RankingScore]) -> List[RankingScore]:
        """Sort scores descending and assign rank integers (1-based)."""
        ordered = sorted(scores, key=lambda s: s.overall_score, reverse=True)
        return [
            RankingScore(
                strategy_id=s.strategy_id,
                opportunity_id=s.opportunity_id,
                strategy_score=s.strategy_score,
                opportunity_score=s.opportunity_score,
                risk_score=s.risk_score,
                robustness_score=s.robustness_score,
                confidence_score=s.confidence_score,
                historical_score=s.historical_score,
                overall_score=s.overall_score,
                rank=i + 1,
            )
            for i, s in enumerate(ordered)
        ]

    # ── private ───────────────────────────────────────────────────────────────

    def _risk_score(
        self, c: StrategyCandidate, suit: SuitabilityResult
    ) -> float:
        # Higher sharpe → better; lower drawdown → better
        sharpe_s = clamp((c.sharpe_ratio / 2.5) * 100.0)     # normalise to ~[0,100]
        dd_s = clamp((1.0 - c.max_drawdown / 0.40) * 100.0)  # 40% DD = 0 score
        risk_compat = suit.compatibility.risk_compatibility
        return 0.40 * sharpe_s + 0.40 * dd_s + 0.20 * risk_compat
