"""iios/investment/strategy/opportunity/lifecycle_history.py
Thread-safe store of all lifecycle events across all opportunities.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from iios.investment.strategy.opportunity.strategy_opportunity import (
    OpportunityState, StateTransitionRecord
)


@dataclass(frozen=True)
class LifecycleEvent:
    """Immutable record of a single lifecycle state transition."""
    opportunity_id: str
    strategy_id:    str
    from_state:     OpportunityState
    to_state:       OpportunityState
    reason:         str
    triggered_by:   str
    occurred_at:    datetime

    def to_dict(self):
        return {
            "opportunity_id": self.opportunity_id,
            "strategy_id":    self.strategy_id,
            "from_state":     self.from_state.value,
            "to_state":       self.to_state.value,
            "reason":         self.reason,
            "triggered_by":   self.triggered_by,
            "occurred_at":    self.occurred_at.isoformat(),
        }


class LifecycleHistory:
    """
    Append-only ring buffer of lifecycle events.
    Indexed by opportunity_id for O(1) timeline queries.
    """

    def __init__(self, max_events: int = 10_000) -> None:
        self._max    = max_events
        self._global: Deque[LifecycleEvent] = deque(maxlen=max_events)
        self._by_opp: Dict[str, List[LifecycleEvent]] = {}
        self._lock   = threading.RLock()

    def record(
        self,
        opportunity_id: str,
        strategy_id: str,
        transition: StateTransitionRecord,
    ) -> None:
        event = LifecycleEvent(
            opportunity_id=opportunity_id,
            strategy_id=strategy_id,
            from_state=transition.from_state,
            to_state=transition.to_state,
            reason=transition.reason,
            triggered_by=transition.triggered_by,
            occurred_at=transition.transitioned_at,
        )
        with self._lock:
            self._global.append(event)
            self._by_opp.setdefault(opportunity_id, []).append(event)

    def timeline(self, opportunity_id: str) -> List[LifecycleEvent]:
        with self._lock:
            return list(self._by_opp.get(opportunity_id, []))

    def recent(self, n: int = 50) -> List[LifecycleEvent]:
        with self._lock:
            buf = list(self._global)
            return buf[-n:]

    def state_counts(self) -> Dict[str, int]:
        """Return count of transitions into each state across all events."""
        with self._lock:
            counts: Dict[str, int] = {}
            for ev in self._global:
                k = ev.to_state.value
                counts[k] = counts.get(k, 0) + 1
            return counts

    def purge(self, opportunity_id: str) -> None:
        with self._lock:
            self._by_opp.pop(opportunity_id, None)
