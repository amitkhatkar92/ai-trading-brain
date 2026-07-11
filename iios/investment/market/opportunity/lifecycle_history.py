"""iios/investment/market/opportunity/lifecycle_history.py
History of lifecycle transitions across all opportunities.
"""
from __future__ import annotations

from collections import deque
from typing import Iterator, List, Optional

from iios.investment.market.opportunity.models import OpportunityEvent, OpportunityEventType


class LifecycleHistory:
    """Stores :class:`OpportunityEvent` records (newest-last)."""

    def __init__(self, maxlen: int = 500) -> None:
        self._buffer: deque[OpportunityEvent] = deque(maxlen=maxlen)

    def append(self, event: OpportunityEvent) -> None:
        self._buffer.append(event)

    def extend(self, events: List[OpportunityEvent]) -> None:
        for e in events:
            self._buffer.append(e)

    def latest(self) -> Optional[OpportunityEvent]:
        return self._buffer[-1] if self._buffer else None

    def recent(self, n: int) -> List[OpportunityEvent]:
        return list(self._buffer)[-n:]

    def by_type(self, event_type: OpportunityEventType) -> List[OpportunityEvent]:
        return [e for e in self._buffer if e.event_type is event_type]

    def for_symbol(self, symbol: str) -> List[OpportunityEvent]:
        return [e for e in self._buffer if e.symbol == symbol]

    def confirmations(self) -> List[OpportunityEvent]:
        return self.by_type(OpportunityEventType.CONFIRMED)

    def expirations(self) -> List[OpportunityEvent]:
        return self.by_type(OpportunityEventType.EXPIRED)

    def __len__(self) -> int:
        return len(self._buffer)
