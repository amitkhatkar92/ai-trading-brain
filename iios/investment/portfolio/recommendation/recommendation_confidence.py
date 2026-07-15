"""iios/investment/portfolio/recommendation/recommendation_confidence.py

Confidence calculation for portfolio recommendations.
"""
from __future__ import annotations

from iios.investment.portfolio.recommendation.recommendation_types import (
    PortfolioIntelligence,
    RecommendationAction, RecommendationPriority,
)


def calculate_confidence(
    base_confidence:       float,
    n_evidence:            int,
    signal_confidence:     float,
    intelligence_quality:  float,
    priority:              RecommendationPriority,
) -> float:
    """
    Compute final confidence for a recommendation.

    Parameters
    ----------
    base_confidence     : initial confidence from rule evaluation [0, 1]
    n_evidence          : number of supporting evidence items
    signal_confidence   : confidence in the market/portfolio signal [0, 1]
    intelligence_quality: quality/completeness of the portfolio intelligence [0, 1]
    priority            : recommendation priority (higher = more confident)

    Returns
    -------
    float: adjusted confidence [0, 1]
    """
    # Priority boost
    priority_boost = {
        RecommendationPriority.IMMEDIATE:     0.10,
        RecommendationPriority.HIGH:          0.05,
        RecommendationPriority.MEDIUM:        0.0,
        RecommendationPriority.LOW:          -0.05,
        RecommendationPriority.INFORMATIONAL:-0.10,
    }.get(priority, 0.0)

    # Evidence boost: each additional evidence item adds a small boost
    evidence_boost = min(0.10, n_evidence * 0.025)

    # Signal and quality adjust the base confidence
    adjusted = (
        base_confidence * 0.50
        + signal_confidence * 0.25
        + intelligence_quality * 0.25
    )
    adjusted += priority_boost + evidence_boost

    return max(0.0, min(1.0, round(adjusted, 4)))


def intelligence_quality_score(intel: PortfolioIntelligence) -> float:
    """
    Estimate the quality/completeness of the portfolio intelligence snapshot.
    Returns a score in [0, 1].
    """
    score = 0.0
    n_components = 8

    # Construction
    if intel.n_positions > 0:
        score += 1.0 / n_components

    # Allocation
    weights_sum = intel.equity_weight + intel.bond_weight + intel.cash_weight
    if 0.95 <= weights_sum <= 1.05:
        score += 1.0 / n_components

    # Optimization
    if intel.optimization_quality > 0:
        score += 1.0 / n_components

    # Diversification
    if intel.hhi > 0 and intel.effective_positions > 0:
        score += 1.0 / n_components

    # Risk
    if intel.risk_budget_utilization > 0:
        score += 1.0 / n_components

    # Performance
    if intel.sharpe_ratio != 0.0 or intel.alpha != 0.0:
        score += 1.0 / n_components

    # Rebalancing
    if intel.drift_level != "":
        score += 1.0 / n_components

    # Decision intelligence
    if intel.market_regime != "" or intel.signal_confidence > 0:
        score += 1.0 / n_components

    return round(min(1.0, score), 4)
