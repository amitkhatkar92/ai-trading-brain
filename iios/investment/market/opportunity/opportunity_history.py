"""iios/investment/market/opportunity/opportunity_history.py
Ring buffer of OpportunitySnapshotData records.
"""
from __future__ import annotations

from collections import deque
from typing import Iterator, List, Optional

from iios.investment.market.opportunity.models import OpportunitySnapshotData


class OpportunityHistory:
    def __init__(self, maxlen: int = 250) -> None:
        self._buffer: deque[OpportunitySnapshotData] = deque(maxlen=maxlen)

    def append(self, snap: OpportunitySnapshotData) -> None:
        self._buffer.append(snap)

    def latest(self) -> Optional[OpportunitySnapshotData]:
        return self._buffer[-1] if self._buffer else None

    def recent(self, n: int) -> List[OpportunitySnapshotData]:
        return list(self._buffer)[-n:]

    def new_count_series(self, n: int) -> List[int]:
        """New-opportunity counts over last n bars."""
        return [s.new_count for s in list(self._buffer)[-n:]]

    def __len__(self) -> int:
        return len(self._buffer)

    def __iter__(self) -> Iterator[OpportunitySnapshotData]:
        return iter(self._buffer)
