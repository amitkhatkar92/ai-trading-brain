"""iios/integration/market_data/providers/alpha_vantage_provider.py

Skeleton for Alpha Vantage — global equities & forex.
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


class AlphaVantageProvider(BaseMarketDataProvider):
    """Alpha Vantage provider skeleton — global stocks, forex, crypto, indicators."""

    _PROVIDER_ID = "alpha_vantage"

    def __init__(self) -> None:
        super().__init__()
        self._capabilities = ProviderCapabilities(
            exchanges = [Exchange.NYSE, Exchange.NASDAQ, Exchange.GLOBAL],
            instrument_types = [
                InstrumentType.EQUITY, InstrumentType.CURRENCY,
                InstrumentType.CRYPTO, InstrumentType.ETF,
            ],
            data_types = [MarketDataType.CANDLE, MarketDataType.SNAPSHOT],
            supports_streaming    = False,
            supports_historical   = True,
            historical_depth_days = 7300,
            supported_intervals   = [
                CandleInterval.M1, CandleInterval.M5, CandleInterval.M15,
                CandleInterval.M30, CandleInterval.H1, CandleInterval.D1,
                CandleInterval.W1, CandleInterval.MN1,
            ],
            supports_snapshots       = True,
            requires_authentication  = True,
            requests_per_minute      = 5,   # free tier limit
        )
        self._metadata = ProviderMetadata(
            provider_id  = self._PROVIDER_ID,
            display_name = "Alpha Vantage",
            description  = "Free & premium global financial market data.",
            vendor       = "Alpha Vantage Inc.",
            vendor_url   = "https://www.alphavantage.co",
            is_free      = True,
            tags         = ["global", "fundamentals", "forex", "indicators"],
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
        raise NotImplementedError("AlphaVantageProvider.fetch_snapshot not yet wired.")

    async def fetch_historical(
        self, symbol: str, start: float, end: float, interval: CandleInterval
    ) -> list[MarketCandle]:
        raise NotImplementedError("AlphaVantageProvider.fetch_historical not yet wired.")

    async def stream_quotes(self, symbols: list[str]) -> AsyncGenerator[MarketQuote, None]:
        raise NotImplementedError("AlphaVantage does not support streaming.")
        if False:  # pragma: no cover
            yield MarketQuote()

    async def stream_trades(self, symbols: list[str]) -> AsyncGenerator[MarketTrade, None]:
        raise NotImplementedError("AlphaVantage does not support trade streaming.")
        if False:  # pragma: no cover
            yield MarketTrade()

    async def stream_order_book(self, symbols: list[str]) -> AsyncGenerator[OrderBook, None]:
        raise NotImplementedError("AlphaVantage does not support order book streaming.")
        if False:  # pragma: no cover
            yield OrderBook()

    async def stream_candles(
        self, symbols: list[str], interval: CandleInterval
    ) -> AsyncGenerator[MarketCandle, None]:
        raise NotImplementedError("AlphaVantage does not support candle streaming.")
        if False:  # pragma: no cover
            yield MarketCandle()

    async def health_check(self) -> ProviderHealth:
        return self._base_health()
