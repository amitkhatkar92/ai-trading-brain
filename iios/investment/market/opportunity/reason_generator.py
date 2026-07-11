"""iios/investment/market/opportunity/reason_generator.py
Generates human-readable discovery reason strings.
"""
from __future__ import annotations

from iios.investment.market.opportunity.models import (
    IntelligenceContext,
    Opportunity,
    OpportunityCategory,
)

_TEMPLATES = {
    OpportunityCategory.TREND_FOLLOWING: (
        "{symbol} is in a confirmed uptrend (strength {ts:.0f}/100) with "
        "relative strength of {rs:.0f}/100 vs the market."
    ),
    OpportunityCategory.BREAKOUT_CANDIDATE: (
        "{symbol} shows breakout signals with volume {vol:.1f}x above average "
        "and RS {rs:.0f}/100. Sector at stage: {ss}."
    ),
    OpportunityCategory.RETEST_CANDIDATE: (
        "{symbol} is retesting a prior level on contracted volume ({vol:.1f}x). "
        "Trend intact ({ts:.0f}/100). Potential continuation opportunity."
    ),
    OpportunityCategory.REVERSAL_CANDIDATE: (
        "{symbol} showing potential reversal: trend weakened ({ts:.0f}/100), "
        "volume spike ({vol:.1f}x). Watch for confirmation."
    ),
    OpportunityCategory.MOMENTUM_CANDIDATE: (
        "{symbol} in momentum mode: RS {rs:.0f}/100, sector RS {srs:.0f}/100, "
        "20-bar return {ret20:+.1f}%."
    ),
    OpportunityCategory.MEAN_REVERSION: (
        "{symbol} oversold relative to market (RS {rs:.0f}/100). "
        "Potential mean reversion if fundamentals intact."
    ),
    OpportunityCategory.SECTOR_ROTATION: (
        "{symbol} sector gaining momentum (RS {srs:.0f}/100, stage: {ss}). "
        "Capital rotation candidate."
    ),
    OpportunityCategory.HIGH_RS: (
        "{symbol} ranks among the highest relative strength names (RS {rs:.0f}/100). "
        "Sector {srs:.0f}/100."
    ),
    OpportunityCategory.RECOVERY_CANDIDATE: (
        "{symbol} recovering from weakness: RS improving to {rs:.0f}/100. "
        "Sector: {ss}."
    ),
    OpportunityCategory.DEFENSIVE_CANDIDATE: (
        "{symbol} is a defensive holding: risk score {risk:.0f}/100, "
        "low volatility regime."
    ),
    OpportunityCategory.OBSERVATION_ONLY: (
        "{symbol} added to watchlist for monitoring. "
        "Insufficient signal strength for active classification."
    ),
}


def generate_reason(opp: Opportunity, ctx: IntelligenceContext) -> str:
    tpl = _TEMPLATES.get(opp.primary_category, _TEMPLATES[OpportunityCategory.OBSERVATION_ONLY])
    return tpl.format(
        symbol=opp.symbol,
        ts=ctx.trend_strength,
        rs=ctx.rs_vs_market,
        vol=ctx.volume_ratio,
        srs=ctx.sector_rs_score,
        ret20=ctx.return_20bar * 100,
        ss=ctx.sector_stage or "unknown",
        risk=ctx.risk_score,
    )


def generate_risk_summary(ctx: IntelligenceContext) -> str:
    parts = []
    if ctx.volatility_percentile >= 0.8:
        parts.append("High volatility")
    elif ctx.volatility_percentile <= 0.3:
        parts.append("Low volatility environment")
    if ctx.systemic_risk_score >= 0.6:
        parts.append("Elevated systemic risk")
    if ctx.risk_score < 40.0:
        parts.append("Risk score below threshold")
    if not parts:
        parts.append("Risk within normal parameters")
    return ". ".join(parts) + "."


def strategy_suitability(opp: Opportunity) -> list:
    """Return list of strategy types this opportunity suits."""
    _MAP = {
        OpportunityCategory.TREND_FOLLOWING:    ["Trend", "Momentum", "Swing"],
        OpportunityCategory.BREAKOUT_CANDIDATE: ["Breakout", "Momentum"],
        OpportunityCategory.RETEST_CANDIDATE:   ["Swing", "Trend"],
        OpportunityCategory.REVERSAL_CANDIDATE: ["Reversal", "Counter-trend"],
        OpportunityCategory.MOMENTUM_CANDIDATE: ["Momentum", "Trend"],
        OpportunityCategory.MEAN_REVERSION:     ["Mean Reversion", "Statistical Arb"],
        OpportunityCategory.SECTOR_ROTATION:    ["Sector Rotation", "Macro"],
        OpportunityCategory.HIGH_RS:            ["Momentum", "Growth"],
        OpportunityCategory.RECOVERY_CANDIDATE: ["Swing", "Value"],
        OpportunityCategory.DEFENSIVE_CANDIDATE: ["Defensive", "Income"],
        OpportunityCategory.OBSERVATION_ONLY:   ["Watchlist"],
    }
    return _MAP.get(opp.primary_category, ["General"])
