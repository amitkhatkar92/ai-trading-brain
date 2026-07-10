"""iios/integration/market_data/providers/paper_market_provider.py

Paper/simulated market data provider.

Generates deterministic synthetic data for backtesting and integration testing.
No external connections required.
"""
from __future__ import annotations

import asyncio
import math
import random
import time
from typing import AsyncGenerator

from iios.integration.market_data.core.market_candle    import MarketCandle
from iios.integration.market_data.core.market_quote     import MarketQuote
from iios.integration.market_data.core.market_snapshot  import MarketSnapshot
from iios.integration.market_data.core.market_trade     import MarketTrade, TradeSide
from iios.integration.market_data.core.order_book       import OrderBook, OrderBookLevel
from iios.integration.market_data.market_data_constants import (
    CandleInterval, DataQuality, Exchange, InstrumentType,
    MarketDataProviderStatus, MarketDataType,
)
from iios.integration.market_data.providers.base_market_data_provider import BaseMarketDataProvider
from iios.integration.market_data.providers.market_data_session       import MarketDataSession, SubscriptionHandle
from iios.integration.market_data.providers.provider_capabilities     import ProviderCapabilities
from iios.integration.market_data.providers.provider_health           import ProviderHealth
from iios.integration.market_data.providers.provider_metadata         import ProviderMetadata


_DEFAULT_SEED_PRICE = 1000.0


class PaperMarketProvider(BaseMarketDataProvider):
    """
    Synthetic market data provider for testing and paper trading.

    Generates random-walk prices using a seeded random generator so that
    results are deterministic given the same seed.
    """

    _PROVIDER_ID = "paper_market"

    def __init__(self, seed: int = 42, tick_interval_sec: float = 0.1) -> None:
        super().__init__()
        self._rng              = random.Random(seed)
        self._tick_interval    = tick_interval_sec
        self._prices: dict[str, float] = {}

        self._capabilities = ProviderCapabilities(
            exchanges = [Exchange.GLOBAL],
            instrument_types = list(InstrumentType),
            data_types = list(MarketDataType),
            supports_streaming       = True,
            supports_order_book      = True,
            supports_trade_feed      = True,
            max_symbols_per_stream   = 10_000,
            supports_historical      = True,
            historical_depth_days    = 9999,
            supported_intervals      = list(CandleInterval),
            supports_snapshots       = True,
            requires_authentication  = False,
        )
        self._meta = ProviderMetadata(
            provider_id  = self._PROVIDER_ID,
            display_name = "Paper Market",
            description  = "Synthetic market data for testing and paper trading.",
            vendor       = "IIOS",
            is_free      = True,
            is_demo      = True,
            tags         = ["paper", "simulation", "testing"],
        )

    @property
    def provider_id(self) -> str:
        return self._PROVIDER_ID

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    @property
    def metadata(self) -> ProviderMetadata:
        return self._meta

    async def connect(self) -> None:
        self._connected_at = time.time()
        self._session = MarketDataSession(
            provider_id = self._PROVIDER_ID,
            status      = MarketDataProviderStatus.STREAMING,
        )

    async def disconnect(self) -> None:
        if self._session:
            self._session.status = MarketDataProviderStatus.DISCONNECTED
            self._session = None
        self._prices.clear()

    async def subscribe(self, symbols: list[str], data_types: list[str]) -> SubscriptionHandle:
        self._assert_connected()
        for sym in symbols:
            if sym not in self._prices:
                self._prices[sym] = _DEFAULT_SEED_PRICE
        h = SubscriptionHandle(provider_id=self._PROVIDER_ID, symbols=symbols, data_types=data_types)
        if self._session:
            self._session.add_subscription(h)
        return h

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        if self._session:
            self._session.remove_subscription(handle.handle_id)

    async def fetch_snapshot(self, symbols: list[str]) -> list[MarketSnapshot]:
        self._assert_connected()
        return [self._make_snapshot(sym) for sym in symbols]

    async def fetch_historical(
        self, symbol: str, start: float, end: float, interval: CandleInterval
    ) -> list[MarketCandle]:
        self._assert_connected()
        candles: list[MarketCandle] = []
        step    = 60.0          # 1 minute — simplified
        ts      = start
        price   = self._prices.get(symbol, _DEFAULT_SEED_PRICE)
        while ts < end:
            op = price
            price = price * (1 + self._rng.gauss(0, 0.001))
            hi = max(op, price) * (1 + abs(self._rng.gauss(0, 0.0005)))
            lo = min(op, price) * (1 - abs(self._rng.gauss(0, 0.0005)))
            vol = abs(self._rng.gauss(1_000_000, 200_000))
            candles.append(MarketCandle(
                symbol=symbol, interval=interval,
                timestamp=ts, open=round(op, 2), high=round(hi, 2),
                low=round(lo, 2), close=round(price, 2), volume=round(vol, 2),
                is_complete=True, quality=DataQuality.SYNTHETIC,
                provider_id=self._PROVIDER_ID,
            ))
            ts += step
        return candles

    async def stream_quotes(self, symbols: list[str]) -> AsyncGenerator[MarketQuote, None]:
        self._assert_connected()
        while self.is_connected():
            for sym in symbols:
                yield self._make_quote(sym)
            await asyncio.sleep(self._tick_interval)

    async def stream_trades(self, symbols: list[str]) -> AsyncGenerator[MarketTrade, None]:
        self._assert_connected()
        while self.is_connected():
            for sym in symbols:
                yield self._make_trade(sym)
            await asyncio.sleep(self._tick_interval)

    async def stream_order_book(self, symbols: list[str]) -> AsyncGenerator[OrderBook, None]:
        self._assert_connected()
        while self.is_connected():
            for sym in symbols:
                yield self._make_order_book(sym)
            await asyncio.sleep(self._tick_interval)

    async def stream_candles(
        self, symbols: list[str], interval: CandleInterval
    ) -> AsyncGenerator[MarketCandle, None]:
        self._assert_connected()
        while self.is_connected():
            for sym in symbols:
                p = self._prices.get(sym, _DEFAULT_SEED_PRICE)
                yield MarketCandle(
                    symbol=sym, interval=interval,
                    timestamp=time.time(), open=p, high=p * 1.001,
                    low=p * 0.999, close=p, volume=1_000,
                    is_complete=False, quality=DataQuality.SYNTHETIC,
                    provider_id=self._PROVIDER_ID,
                )
            await asyncio.sleep(self._tick_interval)

    async def health_check(self) -> ProviderHealth:
        h = self._base_health()
        h.latency_ms = self._rng.uniform(0.5, 2.0)
        return h

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _next_price(self, symbol: str) -> float:
        price = self._prices.get(symbol, _DEFAULT_SEED_PRICE)
        price = price * (1 + self._rng.gauss(0, 0.001))
        price = max(0.01, price)
        self._prices[symbol] = price
        return round(price, 2)

    def _make_quote(self, symbol: str) -> MarketQuote:
        mid = self._next_price(symbol)
        spread = mid * 0.0001
        return MarketQuote(
            symbol=symbol, bid=round(mid - spread, 4), ask=round(mid + spread, 4),
            last=mid, timestamp=time.time(), quality=DataQuality.SYNTHETIC,
            provider_id=self._PROVIDER_ID,
        )

    def _make_trade(self, symbol: str) -> MarketTrade:
        price = self._next_price(symbol)
        return MarketTrade(
            symbol=symbol, price=price,
            size=round(abs(self._rng.gauss(100, 50)), 0),
            side=TradeSide.BUY if self._rng.random() > 0.5 else TradeSide.SELL,
            timestamp=time.time(), quality=DataQuality.SYNTHETIC,
            provider_id=self._PROVIDER_ID,
        )

    def _make_snapshot(self, symbol: str) -> MarketSnapshot:
        p = self._next_price(symbol)
        return MarketSnapshot(
            symbol=symbol, last=p, bid=p * 0.9999, ask=p * 1.0001,
            open=p * 0.995, high=p * 1.005, low=p * 0.993, prev_close=p * 0.997,
            volume=1_000_000, timestamp=time.time(), quality=DataQuality.SYNTHETIC,
            provider_id=self._PROVIDER_ID,
        )

    def _make_order_book(self, symbol: str) -> OrderBook:
        mid = self._next_price(symbol)
        bids = [
            OrderBookLevel(price=round(mid - i * 0.01, 4), size=round(abs(self._rng.gauss(100, 30)), 0))
            for i in range(1, 6)
        ]
        asks = [
            OrderBookLevel(price=round(mid + i * 0.01, 4), size=round(abs(self._rng.gauss(100, 30)), 0))
            for i in range(1, 6)
        ]
        return OrderBook(
            symbol=symbol, bids=bids, asks=asks,
            timestamp=time.time(), quality=DataQuality.SYNTHETIC,
            provider_id=self._PROVIDER_ID,
        )
