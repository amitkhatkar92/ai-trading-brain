"""iios/investment/strategy/opportunity/strategy_matcher.py
StrategyMatcher — scores one StrategyCandidate against one opportunity.
The core of the pluggable matching framework.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import (
    MarketOpportunity, VolatilityRegime,
)
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.matching_profile import MatchingProfile

# Volatility regime ordering (higher index = higher volatility)
_VOL_ORDER = {
    VolatilityRegime.LOW.value:      0,
    VolatilityRegime.MODERATE.value: 1,
    VolatilityRegime.HIGH.value:     2,
    VolatilityRegime.EXTREME.value:  3,
}


@dataclass(frozen=True)
class MatchResult:
    """Detailed result of matching one strategy to one opportunity."""
    strategy_id:       str
    opportunity_id:    str
    score:             float          # 0–100
    passed:            bool
    dimension_scores:  Dict[str, float] = field(default_factory=dict)
    hard_rejected:     bool = False
    rejection_reason:  Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":      self.strategy_id,
            "opportunity_id":   self.opportunity_id,
            "score":            self.score,
            "passed":           self.passed,
            "dimension_scores": self.dimension_scores,
            "hard_rejected":    self.hard_rejected,
            "rejection_reason": self.rejection_reason,
        }


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


class StrategyMatcher:
    """
    Scores a StrategyCandidate against a MarketOpportunity or CompanyOpportunity.

    The class is stateless — safe to share across threads.
    Implements the default deterministic matching algorithm.
    External callers may substitute a different matcher implementing the same
    `.match()` interface to swap the matching policy.
    """

    def match(
        self,
        candidate: StrategyCandidate,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
        profile: MatchingProfile,
    ) -> MatchResult:
        if isinstance(opportunity, MarketOpportunity):
            return self._match_market(candidate, opportunity, profile)
        return self._match_company(candidate, opportunity, profile)

    # ── market opportunity matching ──────────────────────────────────────────

    def _match_market(
        self,
        c: StrategyCandidate,
        opp: MarketOpportunity,
        p: MatchingProfile,
    ) -> MatchResult:
        oid = opp.opportunity_id

        # ── pre-flight guards ────────────────────────────────────────────────
        if opp.confidence < p.min_opp_confidence:
            return self._hard_reject(c, oid, f"confidence {opp.confidence:.2f} < {p.min_opp_confidence:.2f}")
        if opp.liquidity_score < p.min_opp_liquidity:
            return self._hard_reject(c, oid, f"liquidity {opp.liquidity_score:.2f} < {p.min_opp_liquidity:.2f}")
        if not c.is_eligible:
            return self._hard_reject(c, oid, f"strategy approval_status={c.approval_status}")

        weights = p.normalized_weights()
        dims: Dict[str, float] = {}

        # ── regime ──────────────────────────────────────────────────────────
        if c.supports_regime(opp.regime.value):
            dims["regime"] = 100.0
        else:
            dims["regime"] = max(0.0, 100.0 - p.regime_mismatch_penalty)

        # ── timeframe ────────────────────────────────────────────────────────
        dims["timeframe"] = 100.0 if c.supports_timeframe(opp.timeframe.value) else 0.0

        # ── direction ────────────────────────────────────────────────────────
        if c.supports_direction(opp.direction):
            dims["direction"] = 100.0
        else:
            dims["direction"] = max(0.0, 100.0 - p.direction_mismatch_penalty)

        # ── volatility ───────────────────────────────────────────────────────
        dims["volatility"] = self._vol_score(c, opp.volatility_regime.value, p)

        # ── liquidity ────────────────────────────────────────────────────────
        if opp.liquidity_score >= c.min_liquidity_score:
            dims["liquidity"] = 100.0
        else:
            gap = c.min_liquidity_score - opp.liquidity_score
            dims["liquidity"] = _clamp(100.0 - gap * p.liquidity_gap_penalty * 100.0)

        # ── sector ───────────────────────────────────────────────────────────
        dims["sector"] = 100.0 if c.supports_sector(opp.sector) else 50.0

        # ── momentum alignment ───────────────────────────────────────────────
        dims["momentum"] = self._momentum_score(c, opp)

        # ── weighted composite ────────────────────────────────────────────────
        raw = sum(dims[k] * weights.get(k, 0.0) for k in dims)
        score = _clamp(raw)

        if score < p.hard_reject_below:
            return self._hard_reject(c, oid, f"raw score {score:.1f} < hard_reject_below {p.hard_reject_below}")

        return MatchResult(
            strategy_id=c.strategy_id,
            opportunity_id=oid,
            score=round(score, 2),
            passed=score >= p.min_matching_score,
            dimension_scores=dims,
        )

    # ── company opportunity matching ─────────────────────────────────────────

    def _match_company(
        self,
        c: StrategyCandidate,
        opp: CompanyOpportunity,
        p: MatchingProfile,
    ) -> MatchResult:
        oid = opp.opportunity_id

        if opp.confidence < p.min_opp_confidence:
            return self._hard_reject(c, oid, f"confidence {opp.confidence:.2f} < {p.min_opp_confidence:.2f}")
        if not c.is_eligible:
            return self._hard_reject(c, oid, f"strategy approval_status={c.approval_status}")

        weights = p.normalized_weights()
        dims: Dict[str, float] = {}

        # Timeframe
        dims["timeframe"] = 100.0 if c.supports_timeframe(opp.timeframe) else 30.0

        # Direction
        dims["direction"] = 100.0 if c.supports_direction(opp.direction) else max(0.0, 100.0 - p.direction_mismatch_penalty)

        # Sector
        dims["sector"] = 100.0 if c.supports_sector(opp.sector) else 50.0

        # Regime — no explicit regime on company opp; use neutral penalty
        dims["regime"] = 70.0

        # Volatility — use market cap as proxy for volatility tolerance
        cap_map = {"large": "low", "mid": "moderate", "small": "high", "micro": "extreme"}
        implied_vol = cap_map.get(opp.market_cap_category, "moderate")
        dims["volatility"] = self._vol_score(c, implied_vol, p)

        # Liquidity — proxy from market cap
        liq_map = {"large": 0.85, "mid": 0.65, "small": 0.45, "micro": 0.25}
        implied_liq = liq_map.get(opp.market_cap_category, 0.50)
        dims["liquidity"] = 100.0 if implied_liq >= c.min_liquidity_score else _clamp(implied_liq / c.min_liquidity_score * 100.0)

        # Quality alignment
        dims["momentum"] = _clamp(opp.composite_score * 100.0)

        raw = sum(dims[k] * weights.get(k, 0.0) for k in dims)
        score = _clamp(raw)

        if score < p.hard_reject_below:
            return self._hard_reject(c, oid, f"raw score {score:.1f} < hard_reject_below")

        return MatchResult(
            strategy_id=c.strategy_id,
            opportunity_id=oid,
            score=round(score, 2),
            passed=score >= p.min_matching_score,
            dimension_scores=dims,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    def _vol_score(
        self, c: StrategyCandidate, market_vol: str, p: MatchingProfile
    ) -> float:
        order = _VOL_ORDER
        mv = order.get(market_vol, 1)
        min_v = order.get(c.min_volatility_regime, 0) if c.min_volatility_regime else 0
        max_v = order.get(c.max_volatility_regime, 3) if c.max_volatility_regime else 3
        if min_v <= mv <= max_v:
            return 100.0
        distance = min(abs(mv - min_v), abs(mv - max_v))
        return _clamp(100.0 - distance * 25.0)

    def _momentum_score(
        self, c: StrategyCandidate, opp: MarketOpportunity
    ) -> float:
        """Score alignment between strategy direction and market momentum."""
        if "momentum" not in c.tags and "trend" not in c.tags:
            return 75.0  # not momentum-dependent → neutral
        # Momentum score: opp.momentum_score in [−1, 1]; long → positive better
        if opp.direction == "long":
            return _clamp((opp.momentum_score + 1.0) / 2.0 * 100.0)
        if opp.direction == "short":
            return _clamp((-opp.momentum_score + 1.0) / 2.0 * 100.0)
        return 75.0

    @staticmethod
    def _hard_reject(
        c: StrategyCandidate, oid: str, reason: str
    ) -> MatchResult:
        return MatchResult(
            strategy_id=c.strategy_id,
            opportunity_id=oid,
            score=0.0,
            passed=False,
            hard_rejected=True,
            rejection_reason=reason,
        )
