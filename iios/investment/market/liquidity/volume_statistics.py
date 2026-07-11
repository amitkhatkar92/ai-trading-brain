"""iios/investment/market/liquidity/volume_statistics.py
Rolling volume statistics computed over a deque of volume floats.
"""
from __future__ import annotations

import logging
import math
from collections import deque
from typing import List

from iios.investment.market.liquidity.models import VolumeLevel

logger = logging.getLogger(__name__)


class VolumeStatistics:
    """
    Rolling volume statistics computed over a deque of volume floats.
    All computations are O(n) or better.
    """

    def __init__(self, window: int = 20) -> None:
        self._window = window
        self._volumes: deque[float] = deque(maxlen=window)

    def update(self, volume: float) -> None:
        self._volumes.append(volume)

    @property
    def count(self) -> int:
        return len(self._volumes)

    @property
    def avg(self) -> float:
        if not self._volumes:
            return 0.0
        return sum(self._volumes) / len(self._volumes)

    @property
    def std(self) -> float:
        if len(self._volumes) < 2:
            return 0.0
        mean = self.avg
        variance = sum((v - mean) ** 2 for v in self._volumes) / len(self._volumes)
        return math.sqrt(variance)

    @property
    def median(self) -> float:
        if not self._volumes:
            return 0.0
        sorted_vols = sorted(self._volumes)
        n = len(sorted_vols)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_vols[mid - 1] + sorted_vols[mid]) / 2.0
        return float(sorted_vols[mid])

    @property
    def peak(self) -> float:
        if not self._volumes:
            return 0.0
        return max(self._volumes)

    @property
    def minimum(self) -> float:
        if not self._volumes:
            return 0.0
        return min(self._volumes)

    def recent_avg(self, n: int = 5) -> float:
        """Average of last n items."""
        if not self._volumes:
            return 0.0
        items = list(self._volumes)[-n:]
        return sum(items) / len(items)

    def relative(self, volume: float) -> float:
        """volume / avg, 1.0 if avg == 0."""
        avg = self.avg
        if avg == 0.0:
            return 1.0
        return volume / avg

    def normalized(self, volume: float) -> float:
        """volume / peak, clamped [0, 1]."""
        pk = self.peak
        if pk == 0.0:
            return 0.0
        return min(1.0, volume / pk)

    def classify(self, volume: float) -> VolumeLevel:
        """Classify a volume value relative to the rolling average."""
        avg = self.avg
        if avg == 0.0 or volume == 0.0:
            return VolumeLevel.NONE
        ratio = volume / avg
        if ratio > 3.0:
            return VolumeLevel.EXTREME_HIGH
        if ratio > 2.0:
            return VolumeLevel.VERY_HIGH
        if ratio > 1.5:
            return VolumeLevel.HIGH
        if ratio > 1.2:
            return VolumeLevel.ABOVE_AVERAGE
        if ratio > 0.8:
            return VolumeLevel.AVERAGE
        if ratio > 0.5:
            return VolumeLevel.BELOW_AVERAGE
        return VolumeLevel.LOW
