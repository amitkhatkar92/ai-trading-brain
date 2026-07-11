"""iios/investment/market/opportunity/opportunity_classifier.py
Classify a single asset observation into opportunity categories.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.market.opportunity.models import (
    AssetObservation,
    Opportunity,
    OpportunityCategory,
    OpportunityLifecycleStage,
    OpportunityPriority,
)
from iios.investment.market.opportunity.opportunity_category import (
    CategoryRule,
    BUILT_IN_RULES,
    classify_context,
)

_OBSERVATION_THRESHOLD = 40.0   # composite score below which → OBSERVATION_ONLY
_HIGH_PRIORITY_RS_MIN  = 65.0
_CRITICAL_RS_MIN       = 80.0


def _initial_priority(
    primary: OpportunityCategory,
    rs: float,
    composite: float,
) -> OpportunityPriority:
    if primary is OpportunityCategory.OBSERVATION_ONLY:
        return OpportunityPriority.LOW
    if rs >= _CRITICAL_RS_MIN and composite >= 75.0:
        return OpportunityPriority.CRITICAL
    if rs >= _HIGH_PRIORITY_RS_MIN and composite >= 65.0:
        return OpportunityPriority.HIGH
    if composite >= 50.0:
        return OpportunityPriority.MEDIUM
    return OpportunityPriority.LOW


def _initial_confidence(ctx, primary: OpportunityCategory) -> float:
    """0-1 initial confidence estimate."""
    if primary is OpportunityCategory.OBSERVATION_ONLY:
        return 0.2
    # Average three signal components
    trend_c  = ctx.trend_strength / 100.0
    rs_c     = ctx.rs_vs_market   / 100.0
    sec_c    = ctx.sector_rs_score / 100.0
    base     = (trend_c * 0.4 + rs_c * 0.4 + sec_c * 0.2)
    return max(0.0, min(1.0, base))


def _composite_score(
    ctx,
    primary: OpportunityCategory,
    rules: List[CategoryRule],
) -> float:
    """Quick composite score (0-100) for initial opportunity quality."""
    if primary is OpportunityCategory.OBSERVATION_ONLY:
        return max(0.0, min(40.0, ctx.rs_vs_market * 0.4))

    rule = next((r for r in rules if r.category is primary), None)
    weight = rule.weight if rule else 1.0

    score = (
        ctx.trend_strength   * 0.25
        + ctx.rs_vs_market   * 0.30
        + ctx.sector_rs_score * 0.20
        + ctx.volume_ratio * 5.0 * 0.10    # ratio 2.0 → 10 pts
        + ctx.risk_score     * 0.10
        + ctx.breadth_score  * 0.05
    )
    return max(0.0, min(100.0, score * weight))


def classify_observation(
    obs: AssetObservation,
    rules: Optional[List[CategoryRule]] = None,
) -> Optional[Opportunity]:
    """Classify one :class:`AssetObservation`.

    Returns an :class:`Opportunity` if the asset meets any category rule,
    else ``None``.
    """
    active_rules = rules or BUILT_IN_RULES
    ctx          = obs.intelligence
    primary, secondary = classify_context(ctx, active_rules)

    score      = _composite_score(ctx, primary, active_rules)
    confidence = _initial_confidence(ctx, primary)
    priority   = _initial_priority(primary, ctx.rs_vs_market, score)

    opp = Opportunity.new(
        symbol=obs.symbol,
        sector=obs.sector,
        industry=obs.industry,
        primary_category=primary,
        bar_index=obs.bar_index,
    )
    opp.secondary_categories = secondary
    opp.priority             = priority
    opp.priority_score       = score
    opp.confidence           = confidence
    opp.composite_score      = score
    opp.market_regime        = ctx.market_regime
    opp.sector_stage         = ctx.sector_stage
    opp.trend_stage          = ctx.trend_stage

    return opp
