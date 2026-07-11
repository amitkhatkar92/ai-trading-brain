"""iios/investment/market/opportunity/opportunity_snapshot.py
Builds OpportunitySnapshotData from engine state.
"""
from __future__ import annotations

import uuid
from typing import Dict, List

from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityAlert,
    OpportunityCategory,
    OpportunityEvent,
    OpportunityPriority,
    OpportunitySnapshotData,
    ScanScope,
)


def build_snapshot(
    bar_index:        int,
    timestamp:        float,
    active_opps:      List[Opportunity],
    new_discoveries:  List[Opportunity],
    expired_opps:     List[Opportunity],
    alerts:           List[OpportunityAlert],
    events:           List[OpportunityEvent],
    market_regime:    str | None = None,
    breadth_regime:   str | None = None,
    scan_scope:       str = ScanScope.FULL_MARKET.value,
) -> OpportunitySnapshotData:
    sorted_opps = sorted(active_opps, key=lambda o: o.rank if o.rank > 0 else 9999)

    high_pri = sum(
        1 for o in sorted_opps
        if o.priority in (OpportunityPriority.HIGH, OpportunityPriority.CRITICAL)
    )
    critical = sum(1 for o in sorted_opps if o.priority is OpportunityPriority.CRITICAL)

    # Top 3 per category
    top_by_cat: Dict[str, List[str]] = {}
    for cat in OpportunityCategory:
        cat_ops = [o for o in sorted_opps if o.primary_category is cat]
        if cat_ops:
            top_by_cat[cat.value] = [o.symbol for o in cat_ops[:3]]

    return OpportunitySnapshotData(
        snapshot_id=str(uuid.uuid4()),
        bar_index=bar_index,
        timestamp=timestamp,
        opportunities=sorted_opps,
        new_discoveries=list(new_discoveries),
        expired=list(expired_opps),
        alerts=list(alerts),
        events=list(events),
        total_active=len(sorted_opps),
        high_priority_count=high_pri,
        critical_count=critical,
        new_count=len(new_discoveries),
        expired_count=len(expired_opps),
        top_by_category=top_by_cat,
        market_regime=market_regime,
        breadth_regime=breadth_regime,
        scan_scope=scan_scope,
    )
