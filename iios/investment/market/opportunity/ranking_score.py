"""iios/investment/market/opportunity/ranking_score.py
Composite ranking score for a single opportunity.
"""
from __future__ import annotations

from iios.investment.market.opportunity.models import (
    IntelligenceContext,
    Opportunity,
    OpportunityCategory,
    RankingScore,
)

_W_TREND    = 0.25
_W_MOMENTUM = 0.25
_W_FLOW     = 0.15
_W_SECTOR   = 0.20
_W_RISK     = 0.10
_W_QUALITY  = 0.05


def score_opportunity(opp: Opportunity, ctx: IntelligenceContext) -> RankingScore:
    """Compute a :class:`RankingScore` from opportunity + intelligence context."""
    # Trend component: trend_strength + rs_vs_market
    trend_score = ctx.trend_strength * 0.6 + ctx.rs_vs_market * 0.4

    # Momentum: multi-bar returns mapped to 0-100
    # 20-bar: each 1% excess → ~5 pts from 50
    ret20_score = 50.0 + ctx.return_20bar * 500.0
    ret20_score = max(0.0, min(100.0, ret20_score))
    momentum_score = (
        ret20_score * 0.5
        + ctx.sector_momentum * 0.3
        + ctx.rs_vs_market * 0.2
    )
    momentum_score = max(0.0, min(100.0, momentum_score))

    # Capital flow / volume
    vol_score  = min(100.0, ctx.volume_ratio * 40.0)      # ratio 2.5 → 100
    liq_score  = ctx.liquidity_score
    flow_score = vol_score * 0.6 + liq_score * 0.4

    # Sector strength
    sector_score = ctx.sector_rs_score * 0.6 + ctx.sector_momentum * 0.4
    sector_score = max(0.0, min(100.0, sector_score))

    # Risk (higher risk_score = safer = better)
    risk_adj = ctx.risk_score * (1.0 - ctx.volatility_percentile * 0.3)
    risk_adj = max(0.0, min(100.0, risk_adj))

    # Quality: fundamental + breadth
    quality_score = ctx.fundamental_score * 0.6 + ctx.breadth_score * 0.4

    # Category weight modifier
    _CAT_WEIGHT: dict = {
        OpportunityCategory.HIGH_RS:            1.10,
        OpportunityCategory.TREND_FOLLOWING:    1.08,
        OpportunityCategory.BREAKOUT_CANDIDATE: 1.05,
        OpportunityCategory.MOMENTUM_CANDIDATE: 1.05,
        OpportunityCategory.SECTOR_ROTATION:    1.03,
        OpportunityCategory.RECOVERY_CANDIDATE: 0.95,
        OpportunityCategory.RETEST_CANDIDATE:   0.98,
        OpportunityCategory.REVERSAL_CANDIDATE: 0.85,
        OpportunityCategory.MEAN_REVERSION:     0.80,
        OpportunityCategory.DEFENSIVE_CANDIDATE: 0.90,
        OpportunityCategory.OBSERVATION_ONLY:   0.60,
    }
    cat_w = _CAT_WEIGHT.get(opp.primary_category, 1.0)

    composite = (
        trend_score    * _W_TREND
        + momentum_score * _W_MOMENTUM
        + flow_score     * _W_FLOW
        + sector_score   * _W_SECTOR
        + risk_adj       * _W_RISK
        + quality_score  * _W_QUALITY
    ) * cat_w
    composite = max(0.0, min(100.0, composite))

    return RankingScore(
        opportunity_id=opp.opportunity_id,
        symbol=opp.symbol,
        composite_score=composite,
        trend_score=trend_score,
        momentum_score=momentum_score,
        flow_score=flow_score,
        sector_score=sector_score,
        risk_adj_score=risk_adj,
        quality_score=quality_score,
    )
