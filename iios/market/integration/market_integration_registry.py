"""
market_integration_registry.py — iios.market.integration
==========================================================
Thread-safe registry of market integration responses and snapshots.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Callable, List, Optional

from .constants import DEFAULT_MAX_REGISTRY, IntegrationStatus
from .exceptions import (
    MarketIntegrationCapacityError,
    MarketIntegrationNotFoundError,
)
from .market_integration_response import MarketIntegrationResponse


class MarketIntegrationRegistry:
    """
    Thread-safe ordered registry of :class:`~.market_integration_response.MarketIntegrationResponse`
    objects, keyed by ``response_id``.

    When capacity is reached the oldest entry is evicted (FIFO).
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_REGISTRY) -> None:
        self._max   = max_entries
        self._lock  = threading.RLock()
        self._store: OrderedDict[str, MarketIntegrationResponse] = OrderedDict()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register(self, response: MarketIntegrationResponse) -> None:
        if not response.response_id:
            raise MarketIntegrationCapacityError(0)
        with self._lock:
            if response.response_id in self._store:
                del self._store[response.response_id]
            elif len(self._store) >= self._max:
                self._store.popitem(last=False)
            self._store[response.response_id] = response

    def remove(self, response_id: str) -> bool:
        with self._lock:
            if response_id in self._store:
                del self._store[response_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, response_id: str) -> Optional[MarketIntegrationResponse]:
        with self._lock:
            return self._store.get(response_id)

    def get_or_raise(self, response_id: str) -> MarketIntegrationResponse:
        r = self.get(response_id)
        if r is None:
            raise MarketIntegrationNotFoundError(response_id)
        return r

    def by_exchange(self, exchange: str) -> List[MarketIntegrationResponse]:
        with self._lock:
            return [r for r in self._store.values() if r.exchange == exchange]

    def by_status(self, status: IntegrationStatus) -> List[MarketIntegrationResponse]:
        with self._lock:
            return [r for r in self._store.values() if r.status == status]

    def by_integration_id(
        self, integration_id: str
    ) -> List[MarketIntegrationResponse]:
        with self._lock:
            return [
                r for r in self._store.values()
                if r.integration_id == integration_id
            ]

    def latest_for_exchange(
        self, exchange: str
    ) -> Optional[MarketIntegrationResponse]:
        matches = self.by_exchange(exchange)
        return matches[-1] if matches else None

    def query(
        self,
        predicate: Callable[[MarketIntegrationResponse], bool],
    ) -> List[MarketIntegrationResponse]:
        with self._lock:
            return [r for r in self._store.values() if predicate(r)]

    def all_responses(self) -> List[MarketIntegrationResponse]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def exists(self, response_id: str) -> bool:
        with self._lock:
            return response_id in self._store

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
