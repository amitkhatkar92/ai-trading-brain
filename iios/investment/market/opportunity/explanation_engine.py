"""iios/investment/market/opportunity/explanation_engine.py
Generates OpportunityExplanation for an opportunity.
"""
from __future__ import annotations

from typing import Dict

from iios.investment.market.opportunity.evidence_collector import collect_evidence
from iios.investment.market.opportunity.models import (
    IntelligenceContext,
    Opportunity,
    OpportunityExplanation,
)
from iios.investment.market.opportunity.reason_generator import (
    generate_reason,
    generate_risk_summary,
    strategy_suitability,
)


def _confidence_explanation(opp: Opportunity, ctx: IntelligenceContext) -> str:
    level = "High" if opp.confidence >= 0.7 else "Moderate" if opp.confidence >= 0.4 else "Low"
    drivers = []
    if ctx.trend_strength >= 60:
        drivers.append("strong trend")
    if ctx.rs_vs_market >= 60:
        drivers.append("high RS")
    if ctx.volume_ratio >= 1.4:
        drivers.append("volume confirmation")
    if ctx.sector_rs_score >= 60:
        drivers.append("sector leadership")
    driver_str = ", ".join(drivers) if drivers else "limited signal confluence"
    return f"{level} confidence ({opp.confidence:.0%}) driven by {driver_str}."


def _market_context(ctx: IntelligenceContext) -> str:
    parts = []
    if ctx.market_regime:
        parts.append(f"Market regime: {ctx.market_regime}")
    if ctx.breadth_regime:
        parts.append(f"Breadth: {ctx.breadth_regime}")
    if ctx.correlation_regime:
        parts.append(f"Correlation: {ctx.correlation_regime}")
    if ctx.volatility_regime:
        parts.append(f"Volatility: {ctx.volatility_regime}")
    return ". ".join(parts) + "." if parts else "Market context not available."


def _summary(opp: Opportunity, ctx: IntelligenceContext) -> str:
    return (
        f"{opp.symbol} ({opp.sector} / {opp.industry}): "
        f"{opp.primary_category.value.replace('_', ' ').title()} | "
        f"Rank #{opp.rank} | "
        f"Score {opp.composite_score:.1f}/100 | "
        f"{opp.lifecycle_stage.value.upper()}"
    )


def explain(opp: Opportunity, ctx: IntelligenceContext) -> OpportunityExplanation:
    """Build a complete :class:`OpportunityExplanation`."""
    return OpportunityExplanation(
        opportunity_id=opp.opportunity_id,
        symbol=opp.symbol,
        summary=_summary(opp, ctx),
        why_discovered=generate_reason(opp, ctx),
        evidence=collect_evidence(ctx),
        risk_summary=generate_risk_summary(ctx),
        confidence_explanation=_confidence_explanation(opp, ctx),
        market_context=_market_context(ctx),
        strategy_suitability=strategy_suitability(opp),
    )


class ExplanationEngine:
    """Generates and caches :class:`OpportunityExplanation` per opportunity."""

    def __init__(self) -> None:
        self._cache: Dict[str, OpportunityExplanation] = {}   # opp_id → explanation
        self._ctx_cache: Dict[str, IntelligenceContext] = {}  # symbol → context

    def update_context(self, symbol: str, ctx: IntelligenceContext) -> None:
        self._ctx_cache[symbol] = ctx

    def explain(self, opp: Opportunity) -> OpportunityExplanation:
        ctx = self._ctx_cache.get(opp.symbol, IntelligenceContext())
        explanation = explain(opp, ctx)
        self._cache[opp.opportunity_id] = explanation
        return explanation

    def get_cached(self, opportunity_id: str) -> "OpportunityExplanation | None":
        return self._cache.get(opportunity_id)
