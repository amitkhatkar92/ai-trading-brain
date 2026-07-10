"""iios/integration/market_data/providers/polygon_provider.py

Skeleton for Polygon.io — US markets, real-time & historical.
"""
from __future__ import annotations

from typing import AsyncGenerator

from iios.integration.market_data.core.market_candle    import MarketCandle
from iios.integration.market_data.core.market_quote     import MarketQuote
from iios.integration.market_data.core.market_snapshot  import MarketSnapshot
from iios.integration.market_data.core.market_trade     import MarketTrade
from iios.integration.market_data.core.order_book       import OrderBook
from iios.integration.market_data.market_data_constants import (
    CandleInterval, Exchange, InstrumentType,
    MarketDataProviderStatus, MarketDataType,
)
from iios.integration.market_data.providers.base_market_data_provider import BaseMarketDataProvider
from iios.integration.market_data.providers.market_data_session       import MarketDataSession, SubscriptionHandle
from iios.integration.market_data.providers.provider_capabilities     import ProviderCapabilities
from iios.integration.market_data.providers.provider_health           import ProviderHealth
from iios.integration.market_data.providers.provider_metadata         import ProviderMetadata


class PolygonProvider(BaseMarketDataProvider):
    """Polygon.io provider skeleton — US equities, options, crypto, forex."""

    _PROVIDER_ID = "polygon_io"

    def __init__(self) -> None:
        super().__init__()
        self._capabilities = ProviderCapabilities(
            exchanges = [Exchange.NYSE, Exchange.NASDAQ, Exchange.CBOE],
            instrument_types = [
                InstrumentType.EQUITY, InstrumentType.OPTIONS,
                InstrumentType.CRYPTO, InstrumentType.CURRENCY,
            ],
            data_types = [
                MarketDataType.TICK, MarketDataType.QUOTE, MarketDataType.TRADE,
                MarketDataType.CANDLE, MarketDataType.SNAPSHOT,
            ],
            supports_streaming      = True,
            supports_order_book     = False,
            supports_trade_feed     = True,
            supports_historical     = True,
            historical_depth_days   = 7300,
            supported_intervals     = [
                CandleInterval.S1, CandleInterval.M1, CandleInterval.M5,
                CandleInterval.M15, CandleInterval.H1, CandleInterval.D1, CandleInterval.W1,
            ],
            supports_snapshots      = True,
            requires_authentication = True,
            requests_per_minute     = 500,
        )
        self._metadata = ProviderMetadata(
            provider_id  = self._PROVIDER_ID,
            display_name = "Polygon.io",
            description  = "Institutional-grade US market data with WebSocket streaming.",
            vendor       = "Polygon.io",
            vendor_url   = "https://polygon.io",
            is_free      = False,
            tags         = ["us", "real-time", "institutional"],
        )

    @property
    def provider_id(self) -> str:
        return self._PROVIDER_ID

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    async def connect(self) -> None:
        self._session = MarketDataSession(
            provider_id=self._PROVIDER_ID, status=MarketDataProviderStatus.CONNECTED
        )

    async def disconnect(self) -> None:
        if self._session:
            self._session.status = MarketDataProviderStatus.DISCONNECTED
            self._session = None

    async def subscribe(self, symbols: list[str], data_types: list[str]) -> SubscriptionHandle:
        self._assert_connected()
        h = SubscriptionHandle(provider_id=self._PROVIDER_ID, symbols=symbols, data_types=data_types)
        if self._session:
            self._session.add_subscription(h)
        return h

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        if self._session:
            self._session.remove_subscription(handle.handle_id)

    async def fetch_snapshot(self, symbols: list[str]) -> list[MarketSnapshot]:
        raise NotImplementedError("PolygonProvider.fetch_snapshot not yet wired.")

    async def fetch_historical(
        self, symbol: str, start: float, end: float, interval: CandleInterval
    ) -> list[MarketCandle]:
        raise NotImplementedError("PolygonProvider.fetch_historical not yet wired.")

    async def stream_quotes(self, symbols: list[str]) -> AsyncGenerator[MarketQuote, None]:
        raise NotImplementedError("PolygonProvider.stream_quotes not yet wired.")
        if False:  # pragma: no cover
            yield MarketQuote()

    async def stream_trades(self, symbols: list[str]) -> AsyncGenerator[MarketTrade, None]:
        raise NotImplementedError("PolygonProvider.stream_trades not yet wired.")
        if False:  # pragma: no cover
            yield MarketTrade()

    async def stream_order_book(self, symbols: list[str]) -> AsyncGenerator[OrderBook, None]:
        raise NotImplementedError("PolygonProvider.stream_order_book not yet wired.")
        if False:  # pragma: no cover
            yield OrderBook()

    async def stream_candles(
        self, symbols: list[str], interval: CandleInterval
    ) -> AsyncGenerator[MarketCandle, None]:
        raise NotImplementedError("PolygonProvider.stream_candles not yet wired.")
        if False:  # pragma: no cover
            yield MarketCandle()

    async def health_check(self) -> ProviderHealth:
        return self._base_health()
