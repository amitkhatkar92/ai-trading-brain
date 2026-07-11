"""iios/investment/market/opportunity/ranking_statistics.py
Statistical summaries over ranking history.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.opportunity.models import OpportunityCategory, RankingScore
from iios.investment.market.opportunity.ranking_history import RankingHistory


def avg_score_by_category(
    opportunities: list,
    n: int = 1,
) -> Dict[str, float]:
    """Average composite score per category from a list of opportunities."""
    totals: Dict[str, float] = {}
    counts: Dict[str, int]   = {}
    for opp in opportunities:
        key = opp.primary_category.value
        totals[key] = totals.get(key, 0.0) + opp.composite_score
        counts[key] = counts.get(key, 0)   + 1
    return {k: totals[k] / counts[k] for k in totals}


def rank_stability(history: RankingHistory, opportunity_id: str, n: int = 10) -> float:
    """0-1 stability score: 1.0 means rank has not changed over last n bars."""
    series = history.symbol_series(opportunity_id, n)
    if len(series) < 2:
        return 1.0
    variance = sum((x - series[0]) ** 2 for x in series) / len(series)
    # Map variance to [0,1] stability; ±10 pts std → 0.5 stability
    return max(0.0, 1.0 - (variance ** 0.5) / 10.0)


def top_stable_opportunities(
    history: RankingHistory,
    opportunity_ids: List[str],
    n: int = 5,
    lookback: int = 10,
) -> List[str]:
    """Return opportunity IDs sorted by (score × stability)."""
    latest = history.latest() or {}
    scored = []
    for oid in opportunity_ids:
        rs  = latest.get(oid)
        if rs is None:
            continue
        stab   = rank_stability(history, oid, lookback)
        value  = rs.composite_score * stab
        scored.append((value, oid))
    scored.sort(reverse=True)
    return [oid for _, oid in scored[:n]]
