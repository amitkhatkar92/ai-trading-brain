"""iios/investment/market/opportunity/opportunity_statistics.py
Statistical summaries over the opportunity history.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.opportunity.models import OpportunitySnapshotData
from iios.investment.market.opportunity.opportunity_history import OpportunityHistory


def avg_active_count(history: OpportunityHistory, n: int = 20) -> float:
    recent = history.recent(n)
    if not recent:
        return 0.0
    return sum(s.total_active for s in recent) / len(recent)


def discovery_rate(history: OpportunityHistory, n: int = 20) -> float:
    """Average new discoveries per bar."""
    recent = history.recent(n)
    if not recent:
        return 0.0
    return sum(s.new_count for s in recent) / len(recent)


def expiry_rate(history: OpportunityHistory, n: int = 20) -> float:
    recent = history.recent(n)
    if not recent:
        return 0.0
    return sum(s.expired_count for s in recent) / len(recent)


def high_priority_trend(history: OpportunityHistory, n: int = 10) -> float:
    """Positive = high-priority count is increasing."""
    recent = history.recent(n)
    if len(recent) < 2:
        return 0.0
    return (recent[-1].high_priority_count - recent[0].high_priority_count) / len(recent)


def category_distribution(history: OpportunityHistory, n: int = 1) -> Dict[str, float]:
    """Average count per category over last n bars."""
    recent = history.recent(n)
    if not recent:
        return {}
    totals: Dict[str, float] = {}
    for snap in recent:
        for cat, syms in snap.top_by_category.items():
            totals[cat] = totals.get(cat, 0.0) + len(syms)
    return {k: v / len(recent) for k, v in totals.items()}
