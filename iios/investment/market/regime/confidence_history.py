"""iios/investment/market/regime/confidence_history.py
Rolling per-market confidence history.
"""
from __future__ import annotations

import math
import threading
from collections import defaultdict, deque
from typing import Dict, Deque, List, Tuple

from iios.investment.market.regime.models import RegimeType


class ConfidenceHistory:
    """Thread-safe rolling per-market confidence history."""

    def __init__(self, max_size: int = 500) -> None:
        self._lock:     threading.RLock                                                  = threading.RLock()
        self._max_size: int                                                              = max_size
        # per market_id: deque of (timestamp, confidence, regime)
        self._data:     Dict[str, Deque[Tuple[float, float, RegimeType]]]                = defaultdict(
            lambda: deque(maxlen=self._max_size)
        )

    def record(
        self,
        market_id: str,
        confidence: float,
        regime: RegimeType,
        timestamp: float,
    ) -> None:
        with self._lock:
            self._data[market_id].append((timestamp, confidence, regime))

    def recent(
        self, market_id: str, n: int = 20
    ) -> List[Tuple[float, float, RegimeType]]:
        """Returns list of (timestamp, confidence, regime), most recent last."""
        with self._lock:
            items = list(self._data.get(market_id, deque()))
            return items[-n:] if len(items) >= n else items

    def avg_confidence(self, market_id: str, n: int = 20) -> float:
        items = self.recent(market_id, n)
        if not items:
            return 0.0
        return sum(c for _, c, _ in items) / len(items)

    def stability_score(self, market_id: str, n: int = 20) -> float:
        """
        1 - coefficient_of_variation of recent confidence values.
        Returns 0.5 if fewer than 2 samples.
        """
        items = self.recent(market_id, n)
        if len(items) < 2:
            return 0.5
        values = [c for _, c, _ in items]
        mean = sum(values) / len(values)
        if mean == 0.0:
            return 0.5
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)
        cv = std / mean
        return max(0.0, min(1.0, 1.0 - cv))

    def all_market_ids(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    def count(self, market_id: str) -> int:
        with self._lock:
            return len(self._data.get(market_id, deque()))
