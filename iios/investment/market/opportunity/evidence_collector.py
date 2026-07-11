"""iios/investment/market/opportunity/evidence_collector.py
Collects supporting evidence from an IntelligenceContext.
"""
from __future__ import annotations

from typing import List

from iios.investment.market.opportunity.models import Evidence, IntelligenceContext


def collect_evidence(ctx: IntelligenceContext) -> List[Evidence]:
    """Return a list of :class:`Evidence` objects from the intelligence context."""
    evidence: List[Evidence] = []

    # Trend
    if ctx.trend_strength >= 60.0:
        evidence.append(Evidence(
            key="trend_strength",
            value=f"{ctx.trend_strength:.1f}",
            weight=0.25,
            description=f"Strong uptrend ({ctx.trend_strength:.0f}/100)",
        ))
    elif ctx.trend_strength <= 35.0:
        evidence.append(Evidence(
            key="trend_weakness",
            value=f"{ctx.trend_strength:.1f}",
            weight=0.20,
            description=f"Weak trend ({ctx.trend_strength:.0f}/100) — mean reversion potential",
        ))

    # Relative Strength
    if ctx.rs_vs_market >= 65.0:
        evidence.append(Evidence(
            key="high_rs",
            value=f"{ctx.rs_vs_market:.1f}",
            weight=0.30,
            description=f"High relative strength vs market ({ctx.rs_vs_market:.0f}/100)",
        ))
    elif ctx.rs_vs_market <= 35.0:
        evidence.append(Evidence(
            key="low_rs",
            value=f"{ctx.rs_vs_market:.1f}",
            weight=0.20,
            description=f"Low relative strength ({ctx.rs_vs_market:.0f}/100)",
        ))

    # Volume
    if ctx.volume_ratio >= 1.5:
        evidence.append(Evidence(
            key="volume_expansion",
            value=f"{ctx.volume_ratio:.2f}x",
            weight=0.15,
            description=f"Volume {ctx.volume_ratio:.1f}x above 20-day average",
        ))
    elif ctx.volume_ratio <= 0.7:
        evidence.append(Evidence(
            key="volume_contraction",
            value=f"{ctx.volume_ratio:.2f}x",
            weight=0.10,
            description=f"Volume contracted to {ctx.volume_ratio:.1f}x — possible retest",
        ))

    # Sector
    if ctx.sector_rs_score >= 65.0:
        evidence.append(Evidence(
            key="sector_leadership",
            value=f"{ctx.sector_rs_score:.1f}",
            weight=0.20,
            description=f"Sector is a leader ({ctx.sector_rs_score:.0f}/100)",
        ))
    if ctx.sector_stage:
        evidence.append(Evidence(
            key="sector_stage",
            value=ctx.sector_stage,
            weight=0.10,
            description=f"Sector lifecycle stage: {ctx.sector_stage}",
        ))

    # Risk
    if ctx.risk_score >= 60.0:
        evidence.append(Evidence(
            key="low_risk",
            value=f"{ctx.risk_score:.1f}",
            weight=0.10,
            description=f"Favourable risk profile ({ctx.risk_score:.0f}/100)",
        ))

    # Volatility
    if ctx.volatility_percentile <= 0.3:
        evidence.append(Evidence(
            key="low_volatility",
            value=f"{ctx.volatility_percentile:.2f}",
            weight=0.08,
            description=f"Low volatility environment (pct: {ctx.volatility_percentile:.2f})",
        ))
    elif ctx.volatility_percentile >= 0.8:
        evidence.append(Evidence(
            key="high_volatility",
            value=f"{ctx.volatility_percentile:.2f}",
            weight=0.08,
            description=f"Elevated volatility (pct: {ctx.volatility_percentile:.2f}) — caution",
        ))

    # Returns
    if ctx.return_20bar > 0.05:
        evidence.append(Evidence(
            key="positive_20bar",
            value=f"{ctx.return_20bar*100:.1f}%",
            weight=0.12,
            description=f"Strong 20-bar return: +{ctx.return_20bar*100:.1f}%",
        ))
    elif ctx.return_20bar < -0.05:
        evidence.append(Evidence(
            key="negative_20bar",
            value=f"{ctx.return_20bar*100:.1f}%",
            weight=0.10,
            description=f"Weak 20-bar return: {ctx.return_20bar*100:.1f}%",
        ))

    return evidence
