"""iios/investment/market/opportunity/market_opportunity.py
In-memory Opportunity registry: CRUD + active-opportunity queries.
"""
from __future__ import annotations

import logging
from typing import Dict, Iterator, List, Optional

from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityLifecycleStage,
    OpportunityPriority,
)

log = logging.getLogger(__name__)


class OpportunityRegistry:
    """Thread-safe (by convention — callers use engine-level lock) in-memory
    store for all live and recently expired opportunities."""

    def __init__(self, max_expired: int = 500) -> None:
        self._active:  Dict[str, Opportunity] = {}       # opportunity_id → Opportunity
        self._by_sym:  Dict[str, str] = {}               # symbol → opportunity_id
        self._expired: List[Opportunity] = []
        self._max_expired = max_expired

    # ── registration ─────────────────────────────────────────────────────────

    def register(self, opp: Opportunity) -> None:
        """Add or replace opportunity for this symbol."""
        # Evict any existing opportunity for the same symbol
        if opp.symbol in self._by_sym:
            old_id = self._by_sym[opp.symbol]
            self._active.pop(old_id, None)

        self._active[opp.opportunity_id] = opp
        self._by_sym[opp.symbol]         = opp.opportunity_id

    def update(self, opp: Opportunity) -> None:
        """Update in-place (opportunity must already be registered)."""
        if opp.opportunity_id in self._active:
            self._active[opp.opportunity_id] = opp
        else:
            self.register(opp)

    def expire(self, opportunity_id: str) -> None:
        opp = self._active.pop(opportunity_id, None)
        if opp:
            self._by_sym.pop(opp.symbol, None)
            self._expired.append(opp)
            if len(self._expired) > self._max_expired:
                self._expired = self._expired[-self._max_expired:]

    def expire_symbol(self, symbol: str) -> None:
        oid = self._by_sym.get(symbol)
        if oid:
            self.expire(oid)

    # ── queries ───────────────────────────────────────────────────────────────

    def get(self, opportunity_id: str) -> Optional[Opportunity]:
        return self._active.get(opportunity_id)

    def get_by_symbol(self, symbol: str) -> Optional[Opportunity]:
        oid = self._by_sym.get(symbol)
        return self._active.get(oid) if oid else None

    def all_active(self) -> List[Opportunity]:
        return list(self._active.values())

    def by_category(self, cat: OpportunityCategory) -> List[Opportunity]:
        return [o for o in self._active.values() if o.primary_category is cat]

    def by_sector(self, sector: str) -> List[Opportunity]:
        return [o for o in self._active.values() if o.sector == sector]

    def by_priority(self, priority: OpportunityPriority) -> List[Opportunity]:
        return [o for o in self._active.values() if o.priority is priority]

    def by_stage(self, stage: OpportunityLifecycleStage) -> List[Opportunity]:
        return [o for o in self._active.values() if o.lifecycle_stage is stage]

    def recently_expired(self, n: int = 20) -> List[Opportunity]:
        return self._expired[-n:]

    def count_active(self) -> int:
        return len(self._active)

    def count_by_priority(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for opp in self._active.values():
            counts[opp.priority.value] = counts.get(opp.priority.value, 0) + 1
        return counts

    def __len__(self) -> int:
        return len(self._active)

    def __iter__(self) -> Iterator[Opportunity]:
        return iter(self._active.values())
