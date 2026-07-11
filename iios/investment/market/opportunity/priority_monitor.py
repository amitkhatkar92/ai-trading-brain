"""iios/investment/market/opportunity/priority_monitor.py
Monitors opportunities by priority level and surfaces high-priority items.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List

from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityPriority,
)


class PriorityMonitor:
    """Maintains priority-bucketed views of active opportunities."""

    def __init__(self, history_len: int = 50) -> None:
        self._by_priority: Dict[OpportunityPriority, List[Opportunity]] = {
            p: [] for p in OpportunityPriority
        }
        self._critical_history: deque[List[str]] = deque(maxlen=history_len)

    def update(self, opportunities: List[Opportunity]) -> None:
        buckets: Dict[OpportunityPriority, List[Opportunity]] = {
            p: [] for p in OpportunityPriority
        }
        for opp in opportunities:
            if opp.is_active():
                buckets[opp.priority].append(opp)
        # Sort each bucket by rank
        for pri, opps in buckets.items():
            buckets[pri] = sorted(opps, key=lambda o: o.rank if o.rank > 0 else 9999)
        self._by_priority = buckets
        self._critical_history.append(
            [o.symbol for o in buckets[OpportunityPriority.CRITICAL]]
        )

    def get(self, priority: OpportunityPriority) -> List[Opportunity]:
        return list(self._by_priority.get(priority, []))

    def critical(self) -> List[Opportunity]:
        return self.get(OpportunityPriority.CRITICAL)

    def high_and_above(self) -> List[Opportunity]:
        return self.get(OpportunityPriority.CRITICAL) + self.get(OpportunityPriority.HIGH)

    def new_critical(self) -> List[str]:
        """Symbols that entered CRITICAL priority since last bar."""
        if len(self._critical_history) < 2:
            return [o.symbol for o in self.critical()]
        prev = set(self._critical_history[-2])
        curr = set(self._critical_history[-1])
        return sorted(curr - prev)
