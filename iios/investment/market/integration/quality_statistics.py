"""iios/investment/market/integration/quality_statistics.py
Statistical functions over a sequence of QualityScore objects.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.integration.models import QualityScore


def avg_overall(scores: List[QualityScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.overall for s in scores) / len(scores)


def avg_completeness(scores: List[QualityScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.completeness for s in scores) / len(scores)


def avg_consistency(scores: List[QualityScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.consistency for s in scores) / len(scores)


def avg_freshness(scores: List[QualityScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.freshness for s in scores) / len(scores)


def avg_reliability(scores: List[QualityScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.reliability for s in scores) / len(scores)


def below_threshold_bars(scores: List[QualityScore], threshold: float = 50.0) -> int:
    return sum(1 for s in scores if s.overall < threshold)


def quality_trend(scores: List[QualityScore]) -> str:
    """Return 'improving' | 'degrading' | 'stable' based on last n bars."""
    if len(scores) < 3:
        return "stable"
    recent  = scores[-3:]
    first   = recent[0].overall
    last    = recent[-1].overall
    delta   = last - first
    if delta > 5.0:
        return "improving"
    if delta < -5.0:
        return "degrading"
    return "stable"


def dimension_breakdown(scores: List[QualityScore]) -> Dict[str, float]:
    return {
        "completeness": avg_completeness(scores),
        "consistency":  avg_consistency(scores),
        "freshness":    avg_freshness(scores),
        "reliability":  avg_reliability(scores),
    }
