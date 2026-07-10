"""iios/investment/market/structure/swing_history.py
Rolling history of swing points with query APIs.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Deque, List, Optional

from iios.investment.market.structure.models import (
    SwingPoint,
    SwingSequence,
    SwingType,
)

logger = logging.getLogger(__name__)


class SwingHistory:
    """Maintains a bounded rolling history of detected swing points."""

    def __init__(self, max_history: int = 200) -> None:
        self._max = max_history
        self._all: Deque[SwingPoint] = deque(maxlen=max_history)

    def add(self, swing: SwingPoint) -> None:
        self._all.append(swing)

    def get_highs(self, n: int = 10) -> List[SwingPoint]:
        """Return the n most recent swing highs (newest first)."""
        highs = [s for s in reversed(self._all) if s.swing_type == SwingType.HIGH]
        return highs[:n]

    def get_lows(self, n: int = 10) -> List[SwingPoint]:
        """Return the n most recent swing lows (newest first)."""
        lows = [s for s in reversed(self._all) if s.swing_type == SwingType.LOW]
        return lows[:n]

    def get_sequence(self) -> SwingSequence:
        """Return SwingSequence with highs and lows (most recent first)."""
        return SwingSequence(
            highs=self.get_highs(50),
            lows=self.get_lows(50),
        )

    def get_last_high(self) -> Optional[SwingPoint]:
        for s in reversed(self._all):
            if s.swing_type == SwingType.HIGH:
                return s
        return None

    def get_last_low(self) -> Optional[SwingPoint]:
        for s in reversed(self._all):
            if s.swing_type == SwingType.LOW:
                return s
        return None

    def get_range(self, from_index: int, to_index: int) -> List[SwingPoint]:
        """Return all swings with bar index in [from_index, to_index]."""
        return [s for s in self._all if from_index <= s.index <= to_index]

    def count(self) -> int:
        return len(self._all)

    def as_list(self, swing_type: Optional[SwingType] = None) -> List[SwingPoint]:
        """All swings in chronological order, optionally filtered by type."""
        if swing_type is None:
            return list(self._all)
        return [s for s in self._all if s.swing_type == swing_type]
