"""iios/investment/market/integration/aggregation_history.py
Ring buffer of AggregationState — tracks state across bars.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from iios.investment.market.integration.aggregation_state import AggregationState


class AggregationHistory:
    """Fixed-length history of AggregationState, newest last."""

    def __init__(self, maxlen: int = 200) -> None:
        self._buf: Deque[AggregationState] = deque(maxlen=maxlen)

    def append(self, state: AggregationState) -> None:
        self._buf.append(state)

    def latest(self) -> Optional[AggregationState]:
        return self._buf[-1] if self._buf else None

    def recent(self, n: int) -> List[AggregationState]:
        states = list(self._buf)
        return states[-n:] if n < len(states) else states

    def trend_strength_series(self, n: int) -> List[float]:
        return [s.trend_strength for s in self.recent(n)]

    def volatility_series(self, n: int) -> List[float]:
        return [s.volatility_percentile for s in self.recent(n)]

    def regime_series(self, n: int) -> List[Optional[str]]:
        return [s.market_regime for s in self.recent(n)]

    def __len__(self) -> int:
        return len(self._buf)
