"""iios/investment/market/opportunity/opportunity_category.py
Category rules: one set of signal thresholds per OpportunityCategory.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from iios.investment.market.opportunity.models import (
    IntelligenceContext,
    OpportunityCategory,
)


@dataclass(frozen=True)
class CategoryRule:
    """Declarative rule that maps signal thresholds to an opportunity category."""
    category:               OpportunityCategory
    # Each field is (min, max) inclusive range
    trend_strength_min:     float = 0.0
    trend_strength_max:     float = 100.0
    rs_vs_market_min:       float = 0.0
    rs_vs_market_max:       float = 100.0
    volume_ratio_min:       float = 0.0
    volume_ratio_max:       float = 1e9
    liquidity_score_min:    float = 0.0
    sector_rs_min:          float = 0.0
    momentum_positive:      Optional[bool] = None   # True=ret>0; False=ret<0; None=any
    volatility_pct_max:     float = 1.0
    risk_score_min:         float = 0.0
    breadth_min:            float = 0.0
    weight:                 float = 1.0             # category importance weight


# ── Built-in rule set ─────────────────────────────────────────────────────────

BUILT_IN_RULES: List[CategoryRule] = [
    CategoryRule(
        category=OpportunityCategory.TREND_FOLLOWING,
        trend_strength_min=60.0,
        rs_vs_market_min=55.0,
        momentum_positive=True,
        breadth_min=0.5,
        weight=1.2,
    ),
    CategoryRule(
        category=OpportunityCategory.BREAKOUT_CANDIDATE,
        trend_strength_min=55.0,
        volume_ratio_min=1.3,
        rs_vs_market_min=55.0,
        momentum_positive=True,
        weight=1.1,
    ),
    CategoryRule(
        category=OpportunityCategory.RETEST_CANDIDATE,
        trend_strength_min=50.0,
        rs_vs_market_min=50.0,
        volume_ratio_min=0.7,
        volume_ratio_max=1.2,   # low volume = healthy pullback / retest
        momentum_positive=True,
        weight=1.0,
    ),
    CategoryRule(
        category=OpportunityCategory.MOMENTUM_CANDIDATE,
        rs_vs_market_min=60.0,
        sector_rs_min=55.0,
        momentum_positive=True,
        trend_strength_min=55.0,
        weight=1.15,
    ),
    CategoryRule(
        category=OpportunityCategory.HIGH_RS,
        rs_vs_market_min=70.0,
        sector_rs_min=60.0,
        weight=1.2,
    ),
    CategoryRule(
        category=OpportunityCategory.SECTOR_ROTATION,
        sector_rs_min=65.0,
        volume_ratio_min=1.1,
        weight=1.0,
    ),
    CategoryRule(
        category=OpportunityCategory.REVERSAL_CANDIDATE,
        trend_strength_max=40.0,
        rs_vs_market_max=40.0,
        volume_ratio_min=1.4,
        weight=0.9,
    ),
    CategoryRule(
        category=OpportunityCategory.MEAN_REVERSION,
        rs_vs_market_max=35.0,
        trend_strength_max=35.0,
        momentum_positive=False,
        risk_score_min=40.0,
        weight=0.8,
    ),
    CategoryRule(
        category=OpportunityCategory.RECOVERY_CANDIDATE,
        rs_vs_market_min=40.0,
        rs_vs_market_max=55.0,
        trend_strength_min=45.0,
        momentum_positive=True,
        weight=0.85,
    ),
    CategoryRule(
        category=OpportunityCategory.DEFENSIVE_CANDIDATE,
        risk_score_min=60.0,
        volatility_pct_max=0.4,
        breadth_min=0.5,
        weight=0.9,
    ),
]


def matches_rule(ctx: IntelligenceContext, rule: CategoryRule) -> bool:
    """Return True when the intelligence context satisfies the category rule."""
    if ctx.trend_strength < rule.trend_strength_min:
        return False
    if ctx.trend_strength > rule.trend_strength_max:
        return False
    if ctx.rs_vs_market < rule.rs_vs_market_min:
        return False
    if ctx.rs_vs_market > rule.rs_vs_market_max:
        return False
    if ctx.volume_ratio < rule.volume_ratio_min:
        return False
    if ctx.volume_ratio > rule.volume_ratio_max:
        return False
    if ctx.liquidity_score < rule.liquidity_score_min:
        return False
    if ctx.sector_rs_score < rule.sector_rs_min:
        return False
    if ctx.volatility_percentile > rule.volatility_pct_max:
        return False
    if ctx.risk_score < rule.risk_score_min:
        return False
    if ctx.above_ma20_pct < rule.breadth_min:
        return False
    if rule.momentum_positive is not None:
        if rule.momentum_positive and ctx.return_1bar <= 0:
            return False
        if not rule.momentum_positive and ctx.return_1bar >= 0:
            return False
    return True


def classify_context(
    ctx: IntelligenceContext,
    rules: Optional[List[CategoryRule]] = None,
) -> tuple[OpportunityCategory, List[OpportunityCategory]]:
    """Return (primary_category, secondary_categories) from intelligence context."""
    active_rules = rules or BUILT_IN_RULES
    matched: List[CategoryRule] = [r for r in active_rules if matches_rule(ctx, r)]

    if not matched:
        return OpportunityCategory.OBSERVATION_ONLY, []

    # Sort by weight desc; primary = highest-weight match
    matched.sort(key=lambda r: r.weight, reverse=True)
    primary    = matched[0].category
    secondary  = [r.category for r in matched[1:] if r.category is not primary]
    return primary, secondary
