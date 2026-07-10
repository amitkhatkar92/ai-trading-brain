"""iios/integration/market_data/providers/yahoo_finance_provider.py

Skeleton provider for Yahoo Finance.
No API calls are made — this is a structural scaffold only.
"""
from __future__ import annotations

from typing import AsyncGenerator

from iios.integration.market_data.core.market_candle    import MarketCandle
from iios.integration.market_data.core.market_quote     import MarketQuote
from iios.integration.market_data.core.market_snapshot  import MarketSnapshot
from iios.integration.market_data.core.market_trade     import MarketTrade
from iios.integration.market_data.core.order_book       import OrderBook
from iios.integration.market_data.market_data_constants import (
    CandleInterval,
    Exchange,
    InstrumentType,
    MarketDataProviderStatus,
    MarketDataType,
)
from iios.integration.market_data.providers.base_market_data_provider import (
    BaseMarketDataProvider,
)
from iios.integration.market_data.providers.market_data_session import (
    MarketDataSession,
    SubscriptionHandle,
)
from iios.integration.market_data.providers.provider_capabilities import ProviderCapabilities
from iios.integration.market_data.providers.provider_health       import ProviderHealth
from iios.integration.market_data.providers.provider_metadata     import ProviderMetadata


class YahooFinanceProvider(BaseMarketDataProvider):
    """
    Yahoo Finance market data provider skeleton.

    Supported instruments : Global equities, indices, ETFs, mutual funds.
    Data quality          : Delayed (15 min) / indicative.
    Authentication        : Not required.
    """

    _PROVIDER_ID = "yahoo_finance"

    def __init__(self) -> None:
        super().__init__()
        self._capabilities = ProviderCapabilities(
            exchanges         = [Exchange.NYSE, Exchange.NASDAQ, Exchange.NSE, Exchange.BSE],
            instrument_types  = [InstrumentType.EQUITY, InstrumentType.INDEX, InstrumentType.ETF],
            data_types        = [MarketDataType.SNAPSHOT, MarketDataType.CANDLE],
            supports_streaming     = False,
            supports_historical    = True,
            supports_snapshots     = True,
            historical_depth_days  = 3650,   # ~10 years
            supported_intervals    = [
                CandleInterval.D1, CandleInterval.W1, CandleInterval.MN1,
                CandleInterval.H1, CandleInterval.M5, CandleInterval.M1,
            ],
            max_snapshot_batch_size = 200,
            requires_authentication = False,
            requests_per_minute     = 100,
        )
        self._metadata = ProviderMetadata(
            provider_id  = self._PROVIDER_ID,
            display_name = "Yahoo Finance",
            description  = "Free delayed market data from Yahoo Finance (via yfinance).",
            vendor       = "Yahoo Inc.",
            vendor_url   = "https://finance.yahoo.com",
            is_free      = True,
            is_demo      = True,
            tags         = ["free", "delayed", "global"],
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
            provider_id = self._PROVIDER_ID,
            status      = MarketDataProviderStatus.CONNECTED,
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
        """Fetch via yfinance Ticker.info — not implemented here."""
        raise NotImplementedError("YahooFinanceProvider.fetch_snapshot not yet wired.")

    async def fetch_historical(
        self, symbol: str, start: float, end: float, interval: CandleInterval
    ) -> list[MarketCandle]:
        """Fetch via yfinance download() — not implemented here."""
        raise NotImplementedError("YahooFinanceProvider.fetch_historical not yet wired.")

    async def stream_quotes(self, symbols: list[str]) -> AsyncGenerator[MarketQuote, None]:
        """Yahoo Finance does not support real-time streaming."""
        raise NotImplementedError("Yahoo Finance does not support real-time quote streaming.")
        if False:  # pragma: no cover
            yield MarketQuote()

    async def stream_trades(self, symbols: list[str]) -> AsyncGenerator[MarketTrade, None]:
        raise NotImplementedError("Yahoo Finance does not support trade streaming.")
        if False:  # pragma: no cover
            yield MarketTrade()

    async def stream_order_book(self, symbols: list[str]) -> AsyncGenerator[OrderBook, None]:
        raise NotImplementedError("Yahoo Finance does not support order book streaming.")
        if False:  # pragma: no cover
            yield OrderBook()

    async def stream_candles(
        self, symbols: list[str], interval: CandleInterval
    ) -> AsyncGenerator[MarketCandle, None]:
        raise NotImplementedError("Yahoo Finance does not support candle streaming.")
        if False:  # pragma: no cover
            yield MarketCandle()

    async def health_check(self) -> ProviderHealth:
        h = self._base_health()
        return h
