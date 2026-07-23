"""
market_intelligence_engine.py — iios.market.analytics
=======================================================
Intelligence summary generation sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List, Optional

from .constants import MarketRegime, SentimentCategory, TrendDirection
from .market_analytics_response import (
    BreadthResult,
    MarketScores,
    RegimeResult,
    RotationResult,
    SentimentResult,
    VolatilityResult,
)


def generate_intelligence_summary(
    market_analysis_id: str,
    exchange:           str,
    regime:             Optional[RegimeResult],
    breadth:            Optional[BreadthResult],
    volatility:         Optional[VolatilityResult],
    sentiment:          Optional[SentimentResult],
    rotation:           Optional[RotationResult],
    scores:             Optional[MarketScores],
) -> str:
    """
    Returns a human-readable intelligence summary string.
    No I/O — purely deterministic text generation.
    """
    parts: List[str] = []

    # Regime
    if regime is not None:
        parts.append(
            f"Market regime is {regime.regime.value} "
            f"(confidence {regime.confidence:.0%}, "
            f"trend {regime.trend_direction.value}, "
            f"strength {regime.trend_strength.value})."
        )
    else:
        parts.append("Market regime undetermined.")

    # Breadth
    if breadth is not None:
        health_str = "healthy" if breadth.is_healthy else "unhealthy"
        parts.append(
            f"Market breadth is {health_str}: "
            f"{breadth.advancing_pct:.1%} advancing, "
            f"{breadth.declining_pct:.1%} declining."
        )

    # Volatility
    if volatility is not None:
        parts.append(
            f"Volatility is {volatility.vol_regime.value} "
            f"(annualised ≈ {volatility.realised_vol * (252**0.5):.1%})."
        )

    # Sentiment
    if sentiment is not None:
        parts.append(
            f"Sentiment is {sentiment.category.value} "
            f"(score {sentiment.sentiment_score:.0f}/100)."
        )

    # Rotation
    if rotation is not None and rotation.leading_sectors:
        leaders = ", ".join(rotation.leading_sectors[:3])
        parts.append(f"Leading sectors: {leaders}.")

    # Scores
    if scores is not None:
        parts.append(
            f"Overall market score: {scores.overall_score:.0f}/100 "
            f"(health {scores.health_score:.0f})."
        )

    return " ".join(parts)


def _key_risks(
    regime:     Optional[RegimeResult],
    breadth:    Optional[BreadthResult],
    volatility: Optional[VolatilityResult],
    sentiment:  Optional[SentimentResult],
) -> List[str]:
    risks: List[str] = []
    from .constants import VolatilityRegime
    if regime and regime.regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR):
        risks.append("Bearish market regime")
    if breadth and not breadth.is_healthy:
        risks.append("Unhealthy market breadth")
    if volatility and volatility.vol_regime in (
        VolatilityRegime.HIGH, VolatilityRegime.EXTREME
    ):
        risks.append(f"Elevated volatility ({volatility.vol_regime.value})")
    if sentiment and sentiment.category in (
        SentimentCategory.EXTREME_FEAR, SentimentCategory.FEAR
    ):
        risks.append("Negative market sentiment")
    return risks or ["No significant risks identified"]


def _key_opportunities(
    regime:  Optional[RegimeResult],
    breadth: Optional[BreadthResult],
    scores:  Optional[MarketScores],
) -> List[str]:
    opps: List[str] = []
    if regime and regime.regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL):
        opps.append("Bullish regime — trend-following strategies favoured")
    if breadth and breadth.is_healthy:
        opps.append("Broad market participation")
    if scores and scores.momentum_score > 65.0:
        opps.append("Strong momentum environment")
    return opps or ["No significant opportunities identified"]
