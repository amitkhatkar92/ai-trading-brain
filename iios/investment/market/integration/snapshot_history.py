"""iios/investment/market/integration/snapshot_history.py
Ring buffer of MarketIntelligenceSnapshot objects.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from iios.investment.market.integration.models import MarketIntelligenceSnapshot


class SnapshotHistory:
    """Fixed-length history of MarketIntelligenceSnapshot, newest last."""

    def __init__(self, maxlen: int = 250) -> None:
        self._buf: Deque[MarketIntelligenceSnapshot] = deque(maxlen=maxlen)

    def append(self, snap: MarketIntelligenceSnapshot) -> None:
        self._buf.append(snap)

    def latest(self) -> Optional[MarketIntelligenceSnapshot]:
        return self._buf[-1] if self._buf else None

    def recent(self, n: int) -> List[MarketIntelligenceSnapshot]:
        items = list(self._buf)
        return items[-n:] if n < len(items) else items

    def confidence_series(self, n: int) -> List[float]:
        return [s.overall_confidence for s in self.recent(n)]

    def quality_series(self, n: int) -> List[float]:
        return [s.quality.overall for s in self.recent(n)]

    def regime_series(self, n: int) -> List[Optional[str]]:
        return [s.market_regime for s in self.recent(n)]

    def __len__(self) -> int:
        return len(self._buf)
