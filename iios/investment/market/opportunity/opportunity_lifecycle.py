"""iios/investment/market/opportunity/opportunity_lifecycle.py
Orchestrates lifecycle tracking for all active opportunities.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from iios.investment.market.opportunity.lifecycle_history import LifecycleHistory
from iios.investment.market.opportunity.lifecycle_tracker import LifecycleTracker
from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityEvent,
    OpportunityLifecycleStage,
)

log = logging.getLogger(__name__)


class OpportunityLifecycleEngine:
    """Manages a :class:`LifecycleTracker` per opportunity and advances
    all of them each bar."""

    def __init__(self) -> None:
        self._trackers: Dict[str, LifecycleTracker] = {}   # opp_id → tracker
        self._history  = LifecycleHistory()

    def update(
        self,
        opportunities: List[Opportunity],
        bar_index: int,
    ) -> Tuple[List[Opportunity], List[OpportunityEvent]]:
        """Advance each opportunity's lifecycle.

        Returns (active_opportunities, new_events).
        Active opportunities exclude EXPIRED and ARCHIVED.
        """
        all_events: List[OpportunityEvent] = []

        for opp in opportunities:
            if opp.opportunity_id not in self._trackers:
                self._trackers[opp.opportunity_id] = LifecycleTracker(opp)
            try:
                events = self._trackers[opp.opportunity_id].advance(bar_index)
                all_events.extend(events)
            except Exception:
                log.exception("Lifecycle error for %s", opp.symbol)

        self._history.extend(all_events)

        active = [o for o in opportunities if o.is_active()]
        return active, all_events

    # ── queries ───────────────────────────────────────────────────────────────

    def history(self) -> LifecycleHistory:
        return self._history

    def remove(self, opportunity_id: str) -> None:
        self._trackers.pop(opportunity_id, None)
