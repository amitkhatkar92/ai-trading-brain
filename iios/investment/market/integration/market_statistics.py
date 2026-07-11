"""iios/investment/market/integration/market_statistics.py
Statistical functions over a sequence of MarketIntelligenceSnapshot objects.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from iios.investment.market.integration.models import MarketIntelligenceSnapshot


def avg_confidence(snapshots: List[MarketIntelligenceSnapshot]) -> float:
    if not snapshots:
        return 0.0
    return sum(s.overall_confidence for s in snapshots) / len(snapshots)


def avg_quality(snapshots: List[MarketIntelligenceSnapshot]) -> float:
    if not snapshots:
        return 0.0
    return sum(s.quality.overall for s in snapshots) / len(snapshots)


def conflict_rate(snapshots: List[MarketIntelligenceSnapshot]) -> float:
    """Fraction of bars that had ≥1 conflict."""
    if not snapshots:
        return 0.0
    return sum(1 for s in snapshots if s.conflicts.total > 0) / len(snapshots)


def regime_distribution(snapshots: List[MarketIntelligenceSnapshot]) -> Dict[str, int]:
    counter: Counter = Counter()
    for s in snapshots:
        key = s.market_regime or "unknown"
        counter[key] += 1
    return dict(counter)


def state_label_distribution(snapshots: List[MarketIntelligenceSnapshot]) -> Dict[str, int]:
    counter: Counter = Counter()
    for s in snapshots:
        counter[s.market_state_label.value] += 1
    return dict(counter)


def critical_conflict_bars(snapshots: List[MarketIntelligenceSnapshot]) -> int:
    return sum(1 for s in snapshots if s.conflicts.critical > 0)


def avg_active_opportunities(snapshots: List[MarketIntelligenceSnapshot]) -> float:
    if not snapshots:
        return 0.0
    return sum(s.active_opportunities for s in snapshots) / len(snapshots)


def coverage_trend(snapshots: List[MarketIntelligenceSnapshot]) -> List[int]:
    """Number of engines received per bar."""
    return [len(s.engines_received) for s in snapshots]
