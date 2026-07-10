"""iios/integration/market_data/providers/base_market_data_provider.py

Abstract base class for all market data providers.

Every plug-in provider must inherit this class and implement all
abstract methods. No actual API calls should appear here.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from iios.integration.market_data.core.market_candle    import MarketCandle
from iios.integration.market_data.core.market_event     import MarketEvent
from iios.integration.market_data.core.market_quote     import MarketQuote
from iios.integration.market_data.core.market_snapshot  import MarketSnapshot
from iios.integration.market_data.core.market_trade     import MarketTrade
from iios.integration.market_data.core.order_book       import OrderBook
from iios.integration.market_data.market_data_constants import (
    CandleInterval,
    MarketDataProviderStatus,
)
from iios.integration.market_data.market_data_exceptions import (
    ProviderConnectionError,
    ProviderNotConnectedError,
)
from iios.integration.market_data.providers.market_data_session import (
    MarketDataSession,
    SubscriptionHandle,
)
from iios.integration.market_data.providers.provider_capabilities import ProviderCapabilities
from iios.integration.market_data.providers.provider_health       import ProviderHealth
from iios.integration.market_data.providers.provider_metadata     import ProviderMetadata

logger = logging.getLogger(__name__)


class BaseMarketDataProvider(ABC):
    """
    Abstract base for all market data providers.

    Lifecycle
    ---------
    1. Instantiate provider (reads config, validates environment)
    2. ``await provider.connect()``
    3. Use: ``subscribe``, ``stream_*``, ``fetch_*``
    4. ``await provider.disconnect()``

    Thread / Task Safety
    --------------------
    All public methods are async.  Providers must be safe to call from
    concurrent tasks, but a single session per provider is expected.
    """

    def __init__(self) -> None:
        self._session:      MarketDataSession | None = None
        self._connected_at: float = 0.0
        self._stats:        dict[str, int | float] = {
            "messages_received":    0,
            "messages_published":   0,
            "errors":               0,
            "reconnects":           0,
        }

    # ── Identity ───────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique machine-readable identifier. Must be stable across restarts."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Capability declaration — populated once at class level."""

    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Static descriptive information."""

    # ── Connection ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the data source.

        Must set session status to CONNECTED / AUTHENTICATED.
        Raises ProviderConnectionError on failure.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Gracefully terminate all streams and close connection.
        """

    # ── Subscriptions ──────────────────────────────────────────────────────────

    @abstractmethod
    async def subscribe(
        self,
        symbols: list[str],
        data_types: list[str],
    ) -> SubscriptionHandle:
        """
        Register interest in the given symbols and data types.

        Returns an opaque handle that can be passed to unsubscribe().
        """

    @abstractmethod
    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        """
        Cancel an active subscription.
        """

    # ── Snapshots ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def fetch_snapshot(self, symbols: list[str]) -> list[MarketSnapshot]:
        """
        Return the latest market snapshot for each symbol.
        """

    # ── Historical ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def fetch_historical(
        self,
        symbol:   str,
        start:    float,          # UTC epoch
        end:      float,          # UTC epoch
        interval: CandleInterval,
    ) -> list[MarketCandle]:
        """
        Return OHLCV candles for the requested period and interval.
        """

    # ── Streaming async generators ─────────────────────────────────────────────

    @abstractmethod
    async def stream_quotes(
        self, symbols: list[str]
    ) -> AsyncGenerator[MarketQuote, None]:
        """
        Yield real-time best-bid/ask updates.
        """
        # Keep this ``yield`` so Python recognises the method as an
        # async generator even in abstract form.
        if False:  # pragma: no cover
            yield MarketQuote()

    @abstractmethod
    async def stream_trades(
        self, symbols: list[str]
    ) -> AsyncGenerator[MarketTrade, None]:
        """
        Yield real-time executed trade prints.
        """
        if False:  # pragma: no cover
            yield MarketTrade()

    @abstractmethod
    async def stream_order_book(
        self, symbols: list[str]
    ) -> AsyncGenerator[OrderBook, None]:
        """
        Yield real-time order book updates.
        """
        if False:  # pragma: no cover
            yield OrderBook()

    @abstractmethod
    async def stream_candles(
        self,
        symbols:  list[str],
        interval: CandleInterval,
    ) -> AsyncGenerator[MarketCandle, None]:
        """
        Yield real-time candle updates (both forming and completed).
        """
        if False:  # pragma: no cover
            yield MarketCandle()

    # ── Health ─────────────────────────────────────────────────────────────────

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Return a snapshot of this provider's health.
        Subclasses should call ``_base_health()`` and extend it.
        """

    # ── Helpers ────────────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._session is not None and self._session.is_connected()

    def _assert_connected(self) -> None:
        if not self.is_connected():
            raise ProviderNotConnectedError(
                f"Provider '{self.provider_id}' is not connected. "
                "Call connect() first."
            )

    def _base_health(self) -> ProviderHealth:
        """Build a ProviderHealth from internal counters."""
        uptime = time.time() - self._connected_at if self._connected_at > 0 else 0.0
        return ProviderHealth(
            provider_id          = self.provider_id,
            is_connected         = self.is_connected(),
            is_authenticated     = self.is_connected(),
            is_streaming         = (
                self._session is not None
                and self._session.status == MarketDataProviderStatus.STREAMING
            ),
            last_message_at      = (
                self._session.last_active if self._session else 0.0
            ),
            active_subscriptions = (
                len(self._session.subscriptions) if self._session else 0
            ),
            error_count          = int(self._stats.get("errors", 0)),
            uptime_sec           = uptime,
        )

    def _on_message_received(self) -> None:
        self._stats["messages_received"] = int(self._stats.get("messages_received", 0)) + 1
        if self._session:
            self._session.touch()

    def _on_error(self, error: Exception) -> None:
        self._stats["errors"] = int(self._stats.get("errors", 0)) + 1
        if self._session:
            self._session.record_error()
        logger.error("[%s] Error: %s", self.provider_id, error)

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status":      (
                self._session.status.value if self._session
                else MarketDataProviderStatus.DISCONNECTED.value
            ),
            **self._stats,
        }
