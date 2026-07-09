"""iios/investment/market/regime/regime_history.py
Thread-safe FIFO store of regime transitions.
"""
from __future__ import annotations

import threading
from collections import deque

from iios.investment.market.market_constants import DEFAULT_HISTORY_SIZE, MarketRegime
from iios.investment.market.market_exceptions import SnapshotNotFoundError
from iios.investment.market.regime.regime_transition import RegimeTransition


class RegimeHistory:
    """Thread-safe append-only ring buffer for RegimeTransition records."""

    def __init__(self, max_size: int = DEFAULT_HISTORY_SIZE) -> None:
        self._lock:     threading.RLock                      = threading.RLock()
        self._max_size: int                                  = max_size
        self._store:    deque[RegimeTransition]              = deque(maxlen=max_size)
        self._index:    dict[str, RegimeTransition]          = {}

    def record(self, transition: RegimeTransition) -> None:
        with self._lock:
            if transition.transition_id in self._index:
                return   # idempotent
            if len(self._store) >= self._max_size:
                oldest = self._store[0]
                self._index.pop(oldest.transition_id, None)
            self._store.append(transition)
            self._index[transition.transition_id] = transition

    def get(self, transition_id: str) -> RegimeTransition:
        with self._lock:
            if transition_id not in self._index:
                raise SnapshotNotFoundError(transition_id)
            return self._index[transition_id]

    def for_market(self, market_id: str) -> list[RegimeTransition]:
        with self._lock:
            return [t for t in self._store if t.market_id == market_id]

    def recent(self, n: int = 10) -> list[RegimeTransition]:
        with self._lock:
            items = list(self._store)
            return items[-n:] if len(items) >= n else items

    def last_for_market(self, market_id: str) -> RegimeTransition | None:
        with self._lock:
            for t in reversed(list(self._store)):
                if t.market_id == market_id:
                    return t
            return None

    def current_regime(self, market_id: str) -> MarketRegime:
        last = self.last_for_market(market_id)
        return last.to_regime if last is not None else MarketRegime.UNKNOWN

    def count(self) -> int:
        with self._lock:
            return len(self._store)
