"""iios/investment/market/market_state/market_state_manager.py
Thread-safe CRUD manager for MarketState objects.
"""
from __future__ import annotations

import threading

from iios.investment.market.market_constants import MarketStatus
from iios.investment.market.market_exceptions import (
    MarketStateAlreadyExistsError,
    MarketStateNotFoundError,
)
from iios.investment.market.market_state.market_state import MarketState


class MarketStateManager:
    """Thread-safe registry and lifecycle manager for market states."""

    def __init__(self) -> None:
        self._lock:   threading.RLock       = threading.RLock()
        self._states: dict[str, MarketState] = {}

    # ── registration ──────────────────────────────────────────────────────────

    def register(
        self,
        market_id: str,
        name:      str  = "",
        *,
        overwrite: bool = False,
    ) -> MarketState:
        with self._lock:
            if not overwrite and market_id in self._states:
                raise MarketStateAlreadyExistsError(market_id)
            state = MarketState(market_id=market_id, name=name or market_id)
            self._states[market_id] = state
            return state

    # ── retrieval ─────────────────────────────────────────────────────────────

    def get(self, market_id: str) -> MarketState:
        with self._lock:
            if market_id not in self._states:
                raise MarketStateNotFoundError(market_id)
            return self._states[market_id]

    def has(self, market_id: str) -> bool:
        with self._lock:
            return market_id in self._states

    def all_markets(self) -> list[str]:
        with self._lock:
            return list(self._states.keys())

    def all_states(self) -> list[MarketState]:
        with self._lock:
            return list(self._states.values())

    def active_markets(self) -> list[MarketState]:
        with self._lock:
            return [s for s in self._states.values() if s.is_trading]

    def count(self) -> int:
        with self._lock:
            return len(self._states)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def open_market(self, market_id: str, trading_date: str = "") -> MarketState:
        with self._lock:
            state = self.get(market_id)
            state.open(trading_date)
            return state

    def close_market(self, market_id: str) -> MarketState:
        with self._lock:
            state = self.get(market_id)
            state.close()
            return state

    def halt_market(self, market_id: str) -> MarketState:
        with self._lock:
            state = self.get(market_id)
            state.halt()
            return state

    def set_status(self, market_id: str, status: MarketStatus) -> MarketState:
        with self._lock:
            state = self.get(market_id)
            state.set_status(status)
            return state

    def remove(self, market_id: str) -> None:
        with self._lock:
            self._states.pop(market_id, None)
