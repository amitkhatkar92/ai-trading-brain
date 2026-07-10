"""iios/integration/market_data/market_data_context.py

Thread-local context for market data operations.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Generator


class _MDThreadLocal(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self.provider_id: str | None  = None
        self.symbol:      str | None  = None
        self.operation:   str | None  = None
        self.started_at:  float | None = None


_tl = _MDThreadLocal()


class MarketDataContextState:
    """Accessor for the thread-local market data context."""

    @staticmethod
    def set(provider_id: str, symbol: str = "", operation: str = "") -> None:
        _tl.provider_id = provider_id
        _tl.symbol      = symbol
        _tl.operation   = operation
        _tl.started_at  = time.time()

    @staticmethod
    def get_provider_id() -> str | None:
        return _tl.provider_id

    @staticmethod
    def get_symbol() -> str | None:
        return _tl.symbol

    @staticmethod
    def get_operation() -> str | None:
        return _tl.operation

    @staticmethod
    def elapsed_ms() -> float:
        if _tl.started_at is None:
            return 0.0
        return (time.time() - _tl.started_at) * 1000.0

    @staticmethod
    def clear() -> None:
        _tl.provider_id = None
        _tl.symbol      = None
        _tl.operation   = None
        _tl.started_at  = None


@contextmanager
def market_data_context(
    provider_id: str, symbol: str = "", operation: str = ""
) -> Generator[None, None, None]:
    """Context manager that sets / clears thread-local market data context."""
    MarketDataContextState.set(provider_id, symbol, operation)
    try:
        yield
    finally:
        MarketDataContextState.clear()
