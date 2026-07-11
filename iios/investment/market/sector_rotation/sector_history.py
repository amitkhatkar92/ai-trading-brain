"""iios/investment/market/sector_rotation/sector_history.py
Ring buffer storing recent SectorIntelligenceSnapshot objects.
"""
from __future__ import annotations

from collections import deque
from typing import Iterator, List, Optional

from iios.investment.market.sector_rotation.models import SectorIntelligenceSnapshot


class SectorHistory:
    """Fixed-length deque of :class:`SectorIntelligenceSnapshot` objects.

    The buffer is indexed newest-last (``history[-1]`` is the most recent).
    """

    def __init__(self, maxlen: int = 250) -> None:
        self._buffer: deque[SectorIntelligenceSnapshot] = deque(maxlen=maxlen)

    def append(self, snap: SectorIntelligenceSnapshot) -> None:
        self._buffer.append(snap)

    def latest(self) -> Optional[SectorIntelligenceSnapshot]:
        return self._buffer[-1] if self._buffer else None

    def recent(self, n: int) -> List[SectorIntelligenceSnapshot]:
        """Return last *n* snapshots (newest last)."""
        return list(self._buffer)[-n:]

    def __len__(self) -> int:
        return len(self._buffer)

    def __iter__(self) -> Iterator[SectorIntelligenceSnapshot]:
        return iter(self._buffer)

    def at_bar(self, bar_index: int) -> Optional[SectorIntelligenceSnapshot]:
        """Return the snapshot with the closest bar_index ≤ bar_index."""
        result: Optional[SectorIntelligenceSnapshot] = None
        for snap in self._buffer:
            if snap.bar_index <= bar_index:
                result = snap
        return result
