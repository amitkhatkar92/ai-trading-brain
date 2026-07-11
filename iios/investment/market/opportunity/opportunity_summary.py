"""iios/investment/market/opportunity/opportunity_summary.py
Builds high-level summary statistics from a list of opportunities.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityLifecycleStage,
    OpportunityPriority,
)


@dataclass
class OpportunitySummary:
    total_active:        int
    by_category:         Dict[str, int]
    by_lifecycle:        Dict[str, int]
    by_priority:         Dict[str, int]
    avg_composite_score: float
    top_symbols:         List[str]         # top 10 by rank
    top_by_category:     Dict[str, List[str]]   # category → top 3 symbols


def build_summary(opportunities: List[Opportunity]) -> OpportunitySummary:
    active = [o for o in opportunities if o.is_active()]
    if not active:
        return OpportunitySummary(
            total_active=0, by_category={}, by_lifecycle={},
            by_priority={}, avg_composite_score=0.0,
            top_symbols=[], top_by_category={},
        )

    by_cat  = Counter(o.primary_category.value for o in active)
    by_lc   = Counter(o.lifecycle_stage.value  for o in active)
    by_pri  = Counter(o.priority.value         for o in active)

    avg_score = sum(o.composite_score for o in active) / len(active)
    sorted_active = sorted(active, key=lambda o: o.rank if o.rank > 0 else 9999)
    top_symbols   = [o.symbol for o in sorted_active[:10]]

    # Top 3 per category
    top_by_cat: Dict[str, List[str]] = {}
    for cat in OpportunityCategory:
        cat_ops = [o for o in sorted_active if o.primary_category is cat]
        if cat_ops:
            top_by_cat[cat.value] = [o.symbol for o in cat_ops[:3]]

    return OpportunitySummary(
        total_active=len(active),
        by_category=dict(by_cat),
        by_lifecycle=dict(by_lc),
        by_priority=dict(by_pri),
        avg_composite_score=avg_score,
        top_symbols=top_symbols,
        top_by_category=top_by_cat,
    )
