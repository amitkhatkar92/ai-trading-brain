"""iios/investment/market/sector_rotation/rotation_history.py
Ring buffer of historical RotationSignal records.
"""
from __future__ import annotations

from collections import deque
from typing import Iterator, List, Optional

from iios.investment.market.sector_rotation.models import RotationSignal, RotationType


class RotationHistory:
    """Stores recent :class:`RotationSignal` objects (newest-last)."""

    def __init__(self, maxlen: int = 100) -> None:
        self._buffer: deque[RotationSignal] = deque(maxlen=maxlen)

    def append(self, signal: RotationSignal) -> None:
        self._buffer.append(signal)

    def latest(self) -> Optional[RotationSignal]:
        return self._buffer[-1] if self._buffer else None

    def recent(self, n: int) -> List[RotationSignal]:
        return list(self._buffer)[-n:]

    def by_type(self, rot_type: RotationType) -> List[RotationSignal]:
        return [s for s in self._buffer if s.rotation_type is rot_type]

    def confirmed_signals(self) -> List[RotationSignal]:
        return [s for s in self._buffer if s.confirmed]

    def __len__(self) -> int:
        return len(self._buffer)

    def __iter__(self) -> Iterator[RotationSignal]:
        return iter(self._buffer)
