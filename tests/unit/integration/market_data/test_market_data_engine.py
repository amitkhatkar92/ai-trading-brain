"""tests/unit/integration/market_data/test_market_data_engine.py

Comprehensive unit tests for the Market Data Provider Framework.

Coverage targets:
- Constants / enums
- All core models
- Provider registration / lifecycle
- Provider capabilities / metadata / health
- Streaming components (buffer, router, dispatcher, manager)
- Validation (gap, duplicate, anomaly, market_validator)
- Normalization
- Cache
- Distribution (publisher)
- Historical data manager
- Market data manager
- Engine lifecycle (start / stop / assert_running)
- Singleton
"""
from __future__ import annotations

import asyncio
import time

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


# ── imports under test ────────────────────────────────────────────────────────

from iios.integration.market_data.market_data_constants import (
    AnomalyType,
    CandleInterval,
    DataQuality,
    Exchange,
    InstrumentType,
    MarketDataEngineStatus,
    MarketDataProviderStatus,
    MarketDataType,
    MarketEventType,
    SubscriptionStatus,
    TradingSession,
    DEFAULT_STREAM_BUFFER_SIZE,
    DEFAULT_CONNECT_TIMEOUT_SEC,
    MARKET_DATA_ENGINE_VERSION,
)
from iios.integration.market_data.market_data_exceptions import (
    HistoricalDataNotAvailableError,
    MarketDataEngineAlreadyRunningError,
    MarketDataEngineNotRunningError,
    MarketDataError,
    MarketDataProviderAlreadyRegisteredError,
    MarketDataProviderNotFoundError,
    MarketDataRegistryError,
    NoProviderForSymbolError,
    ProviderConnectionError,
    ProviderNotConnectedError,
    StreamBufferOverflowError,
    SubscriptionCapacityError,
    SubscriptionNotFoundError,
)
from iios.integration.market_data.market_data_engine import (
    MarketDataEngine,
    get_market_data_engine,
    reset_market_data_engine,
)
from iios.integration.market_data.market_data_context import (
    MarketDataContextState,
    market_data_context,
)
from iios.integration.market_data.market_data_factory import MarketDataFactory
from iios.integration.market_data.market_data_registry import MarketDataRegistry

# Core models
from iios.integration.market_data.core.market_tick      import MarketTick
from iios.integration.market_data.core.market_quote     import MarketQuote
from iios.integration.market_data.core.market_trade     import MarketTrade, TradeSide
from iios.integration.market_data.core.market_candle    import MarketCandle
from iios.integration.market_data.core.order_book       import OrderBook, OrderBookLevel
from iios.integration.market_data.core.market_snapshot  import MarketSnapshot
from iios.integration.market_data.core.market_event     import MarketEvent
from iios.integration.market_data.core.market_statistics import MarketStatistics

# Providers
from iios.integration.market_data.providers.base_market_data_provider import BaseMarketDataProvider
from iios.integration.market_data.providers.provider_capabilities     import ProviderCapabilities
from iios.integration.market_data.providers.provider_metadata         import ProviderMetadata
from iios.integration.market_data.providers.provider_health           import ProviderHealth
from iios.integration.market_data.providers.market_data_session       import MarketDataSession, SubscriptionHandle
from iios.integration.market_data.providers.paper_market_provider     import PaperMarketProvider
from iios.integration.market_data.providers.yahoo_finance_provider    import YahooFinanceProvider
from iios.integration.market_data.providers.nse_provider              import NSEProvider
from iios.integration.market_data.providers.polygon_provider          import PolygonProvider
from iios.integration.market_data.providers.alpha_vantage_provider    import AlphaVantageProvider
from iios.integration.market_data.providers.twelve_data_provider      import TwelveDataProvider

# Streaming
from iios.integration.market_data.streaming.stream_buffer        import StreamBuffer
from iios.integration.market_data.streaming.subscription_manager import SubscriptionManager, SubscriptionRecord
from iios.integration.market_data.streaming.stream_router        import StreamRouter
from iios.integration.market_data.streaming.stream_dispatcher    import StreamDispatcher
from iios.integration.market_data.streaming.stream_manager       import StreamManager

# Validation
from iios.integration.market_data.validation.quality_report      import QualityReport, QualityIssue
from iios.integration.market_data.validation.gap_detector        import GapDetector
from iios.integration.market_data.validation.duplicate_detector  import DuplicateDetector
from iios.integration.market_data.validation.anomaly_detector    import AnomalyDetector
from iios.integration.market_data.validation.market_validator    import MarketValidator

# Normalization
from iios.integration.market_data.normalization.market_normalizer import MarketNormalizer

# Cache
from iios.integration.market_data.cache.market_data_cache import MarketDataCache

# Distribution
from iios.integration.market_data.distribution.market_event_publisher import MarketEventPublisher

# Historical
from iios.integration.market_data.historical.historical_data_manager import HistoricalDataManager

# Monitoring
from iios.integration.market_data.monitoring.market_data_monitor import MarketDataMonitor


# ═════════════════════════════════════════════════════════════════════════════
# 1. Constants & Enums
# ═════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_exchange_values(self):
        assert Exchange.NSE.value == "NSE"
        assert Exchange.NYSE.value == "NYSE"
        assert Exchange.UNKNOWN.value == "UNKNOWN"

    def test_instrument_type_values(self):
        assert InstrumentType.EQUITY.value == "equity"
        assert InstrumentType.OPTIONS.value == "options"

    def test_market_data_type_values(self):
        assert MarketDataType.TICK.value == "tick"
        assert MarketDataType.ORDER_BOOK.value == "order_book"
        assert MarketDataType.SNAPSHOT.value == "snapshot"

    def test_candle_interval_values(self):
        assert CandleInterval.M1.value  == "1m"
        assert CandleInterval.D1.value  == "1d"
        assert CandleInterval.H1.value  == "1h"

    def test_data_quality_values(self):
        assert DataQuality.OFFICIAL.value   == "official"
        assert DataQuality.SYNTHETIC.value  == "synthetic"
        assert DataQuality.STALE.value      == "stale"

    def test_engine_status_values(self):
        assert MarketDataEngineStatus.RUNNING.value  == "running"
        assert MarketDataEngineStatus.STOPPED.value  == "stopped"

    def test_subscription_status_values(self):
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.FAILED.value == "failed"

    def test_anomaly_type_values(self):
        assert AnomalyType.PRICE_SPIKE.value    == "price_spike"
        assert AnomalyType.DUPLICATE.value      == "duplicate"
        assert AnomalyType.GAP_IN_SERIES.value  == "gap_in_series"

    def test_market_event_type_values(self):
        assert MarketEventType.TICK_RECEIVED.value  == "tick_received"
        assert MarketEventType.ENGINE_STARTED.value == "engine_started"

    def test_provider_status_values(self):
        assert MarketDataProviderStatus.CONNECTED.value    == "connected"
        assert MarketDataProviderStatus.DISCONNECTED.value == "disconnected"
        assert MarketDataProviderStatus.STREAMING.value    == "streaming"

    def test_version_constant(self):
        assert MARKET_DATA_ENGINE_VERSION == "1.0.0"

    def test_default_stream_buffer_size(self):
        assert DEFAULT_STREAM_BUFFER_SIZE > 0

    def test_connect_timeout(self):
        assert DEFAULT_CONNECT_TIMEOUT_SEC > 0


# ═════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_root_exception(self):
        e = MarketDataError("test", "MD-000")
        assert e.code    == "MD-000"
        assert "test" in str(e)

    def test_provider_connection_error(self):
        e = ProviderConnectionError("down")
        assert e.code == "MD-011"

    def test_not_found(self):
        e = MarketDataProviderNotFoundError("missing")
        assert e.code == "MD-015"

    def test_already_registered(self):
        e = MarketDataProviderAlreadyRegisteredError("dupe")
        assert e.code == "MD-016"

    def test_subscription_not_found(self):
        e = SubscriptionNotFoundError("x")
        assert e.code == "MD-021"

    def test_engine_not_running(self):
        e = MarketDataEngineNotRunningError("stopped")
        assert e.code == "MD-050"

    def test_engine_already_running(self):
        e = MarketDataEngineAlreadyRunningError("running")
        assert e.code == "MD-051"

    def test_stream_buffer_overflow(self):
        e = StreamBufferOverflowError("full")
        assert e.code == "MD-031"

    def test_no_provider_for_symbol(self):
        e = NoProviderForSymbolError("AAPL")
        assert e.code == "MD-017"

    def test_historical_not_available(self):
        e = HistoricalDataNotAvailableError("none")
        assert e.code == "MD-042"

    def test_subscription_capacity(self):
        e = SubscriptionCapacityError("cap")
        assert e.code == "MD-023"

    def test_repr(self):
        e = ProviderConnectionError("oops")
        assert "MD-011" in repr(e)


# ═════════════════════════════════════════════════════════════════════════════
# 3. Core Models
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketTick:
    def test_defaults(self):
        t = MarketTick(symbol="AAPL", price=150.0, size=100.0)
        assert t.symbol == "AAPL"
        assert t.price  == 150.0
        assert t.tick_id

    def test_age(self):
        t = MarketTick(symbol="X")
        t.received_at = time.time() - 5.0
        assert t.age_sec() > 4.9

    def test_to_dict(self):
        t = MarketTick(symbol="AAPL", price=10.0)
        d = t.to_dict()
        assert d["symbol"] == "AAPL"
        assert "price" in d


class TestMarketQuote:
    def test_mid_computed(self):
        q = MarketQuote(symbol="AAPL", bid=100.0, ask=100.2)
        assert q.mid == pytest.approx(100.1)

    def test_spread(self):
        q = MarketQuote(symbol="AAPL", bid=100.0, ask=100.5)
        assert q.spread() == pytest.approx(0.5)

    def test_spread_pct(self):
        q = MarketQuote(symbol="AAPL", bid=100.0, ask=100.2)
        assert q.spread_pct() > 0

    def test_inverted(self):
        q = MarketQuote(symbol="X", bid=101.0, ask=100.0, mid=100.5)
        assert q.is_inverted()

    def test_not_stale_fresh(self):
        q = MarketQuote(symbol="X")
        assert not q.is_stale(max_age_sec=60.0)

    def test_to_dict(self):
        q = MarketQuote(symbol="X", bid=1.0, ask=1.1)
        d = q.to_dict()
        assert "spread" in d
        assert d["symbol"] == "X"


class TestMarketTrade:
    def test_notional(self):
        t = MarketTrade(symbol="X", price=200.0, size=10.0)
        assert t.notional() == 2000.0

    def test_buyer_initiated(self):
        t = MarketTrade(symbol="X", side=TradeSide.BUY)
        assert t.is_buyer_initiated()

    def test_to_dict(self):
        t = MarketTrade(symbol="X", price=1.0, size=1.0)
        d = t.to_dict()
        assert "notional" in d


class TestMarketCandle:
    def _valid_candle(self) -> MarketCandle:
        return MarketCandle(
            symbol="NIFTY", interval=CandleInterval.M5,
            open=18000, high=18100, low=17900, close=18050,
            volume=500_000, is_complete=True,
        )

    def test_is_valid(self):
        c = self._valid_candle()
        assert c.is_valid()

    def test_invalid_ohlc(self):
        c = MarketCandle(open=100, high=90, low=80, close=95)  # high < open
        assert not c.is_valid()

    def test_body(self):
        c = MarketCandle(open=100, high=110, low=90, close=105)
        assert c.body() == 5.0

    def test_upper_wick(self):
        c = MarketCandle(open=100, high=110, low=90, close=105)
        assert c.upper_wick() == 5.0   # 110 - max(100, 105)

    def test_is_bullish(self):
        c = MarketCandle(open=100, close=105)
        assert c.is_bullish()

    def test_to_dict(self):
        c = self._valid_candle()
        d = c.to_dict()
        assert d["symbol"] == "NIFTY"
        assert "volume" in d


class TestOrderBook:
    def _book(self) -> OrderBook:
        bids = [OrderBookLevel(price=100.0 - i, size=100) for i in range(5)]
        asks = [OrderBookLevel(price=101.0 + i, size=100) for i in range(5)]
        return OrderBook(symbol="X", bids=bids, asks=asks)

    def test_best_bid_ask(self):
        b = self._book()
        assert b.best_bid() == 100.0
        assert b.best_ask() == 101.0

    def test_mid(self):
        b = self._book()
        assert b.mid() == pytest.approx(100.5)

    def test_spread(self):
        b = self._book()
        assert b.spread() == pytest.approx(1.0)

    def test_imbalance(self):
        b = self._book()
        assert abs(b.imbalance()) < 0.01   # equal sizes

    def test_not_crossed(self):
        b = self._book()
        assert not b.is_crossed()

    def test_to_dict(self):
        b = self._book()
        d = b.to_dict()
        assert d["symbol"] == "X"
        assert d["bid_depth"] == 5

    def test_total_bid_size(self):
        b = self._book()
        assert b.total_bid_size() == 500


class TestMarketSnapshot:
    def test_change_computed(self):
        s = MarketSnapshot(symbol="X", last=100.0, prev_close=95.0)
        assert s.change     == pytest.approx(5.0)
        assert s.change_pct == pytest.approx(100.0 * 5 / 95)

    def test_spread(self):
        s = MarketSnapshot(symbol="X", bid=99.5, ask=100.5, last=100.0)
        assert s.spread() == pytest.approx(1.0)

    def test_upper_circuit(self):
        s = MarketSnapshot(symbol="X", last=110.0, circuit_high=110.0)
        assert s.is_upper_circuit()

    def test_to_dict(self):
        s = MarketSnapshot(symbol="X", last=100.0)
        d = s.to_dict()
        assert "change" in d


class TestMarketEvent:
    def test_topic_auto_generated(self):
        e = MarketEvent(
            event_type=MarketEventType.TICK_RECEIVED,
            symbol="AAPL", exchange=Exchange.NASDAQ,
        )
        assert "AAPL" in e.topic

    def test_age_ms(self):
        e = MarketEvent()
        e.published_at = time.time() - 1.0
        assert e.age_ms() > 900

    def test_to_dict(self):
        e = MarketEvent(symbol="X")
        d = e.to_dict()
        assert "event_id" in d

    def test_replay_flag(self):
        e = MarketEvent(is_replay=True)
        assert e.is_replay


class TestMarketStatistics:
    def test_period_seconds(self):
        s = MarketStatistics(period_start=1000.0, period_end=1060.0)
        assert s.period_seconds() == 60.0

    def test_to_dict(self):
        s = MarketStatistics(symbol="X")
        d = s.to_dict()
        assert "stat_id" in d


# ═════════════════════════════════════════════════════════════════════════════
# 4. Provider Capabilities & Metadata
# ═════════════════════════════════════════════════════════════════════════════

class TestProviderCapabilities:
    def test_supports(self):
        caps = ProviderCapabilities(data_types=[MarketDataType.SNAPSHOT])
        assert caps.supports(MarketDataType.SNAPSHOT)
        assert not caps.supports(MarketDataType.TICK)

    def test_supports_exchange_global(self):
        caps = ProviderCapabilities(exchanges=[Exchange.GLOBAL])
        assert caps.supports_exchange(Exchange.NSE)

    def test_supports_interval(self):
        caps = ProviderCapabilities(supported_intervals=[CandleInterval.D1])
        assert caps.supports_interval(CandleInterval.D1)
        assert not caps.supports_interval(CandleInterval.M1)


class TestProviderMetadata:
    def test_to_dict(self):
        m = ProviderMetadata(provider_id="test", display_name="Test", is_free=True)
        d = m.to_dict()
        assert d["is_free"] is True
        assert d["provider_id"] == "test"


class TestProviderHealth:
    def test_healthy(self):
        h = ProviderHealth(provider_id="x", is_connected=True)
        assert h.is_healthy()

    def test_unhealthy_error(self):
        h = ProviderHealth(provider_id="x", is_connected=True, last_error="boom")
        assert not h.is_healthy()

    def test_to_dict(self):
        h = ProviderHealth(provider_id="x", is_connected=True, latency_ms=1.5)
        d = h.to_dict()
        assert d["is_healthy"] is True
        assert d["latency_ms"] == pytest.approx(1.5)


class TestMarketDataSession:
    def test_subscription_add_remove(self):
        sess = MarketDataSession(provider_id="x")
        h = SubscriptionHandle(provider_id="x", symbols=["AAPL"])
        sess.add_subscription(h)
        assert len(sess.subscriptions) == 1
        assert sess.remove_subscription(h.handle_id)
        assert len(sess.subscriptions) == 0

    def test_touch(self):
        sess = MarketDataSession(provider_id="x")
        before = sess.message_count
        sess.touch()
        assert sess.message_count == before + 1

    def test_is_connected_connected_status(self):
        sess = MarketDataSession(provider_id="x", status=MarketDataProviderStatus.CONNECTED)
        assert sess.is_connected()

    def test_is_not_connected_disconnected_status(self):
        sess = MarketDataSession(provider_id="x", status=MarketDataProviderStatus.DISCONNECTED)
        assert not sess.is_connected()

    def test_to_dict(self):
        sess = MarketDataSession(provider_id="x")
        d = sess.to_dict()
        assert "session_id" in d


# ═════════════════════════════════════════════════════════════════════════════
# 5. PaperMarketProvider
# ═════════════════════════════════════════════════════════════════════════════

class TestPaperMarketProvider:
    def setup_method(self):
        self.p = PaperMarketProvider(seed=42)

    def test_provider_id(self):
        assert self.p.provider_id == "paper_market"

    def test_capabilities_streaming(self):
        assert self.p.capabilities.supports_streaming is True

    def test_metadata_is_demo(self):
        assert self.p.metadata.is_demo is True

    def test_not_connected_initially(self):
        assert not self.p.is_connected()

    def test_connect_disconnect(self):
        async def run():
            await self.p.connect()
            assert self.p.is_connected()
            await self.p.disconnect()
            assert not self.p.is_connected()
        _run(run())

    def test_assert_connected_raises(self):
        with pytest.raises(ProviderNotConnectedError):
            self.p._assert_connected()

    def test_subscribe_returns_handle(self):
        async def run():
            await self.p.connect()
            h = await self.p.subscribe(["AAPL"], ["quote"])
            assert h.handle_id
            assert h.provider_id == "paper_market"
            await self.p.disconnect()
        _run(run())

    def test_fetch_snapshot(self):
        async def run():
            await self.p.connect()
            snaps = await self.p.fetch_snapshot(["AAPL", "GOOG"])
            assert len(snaps) == 2
            assert snaps[0].symbol == "AAPL"
            await self.p.disconnect()
        _run(run())

    def test_fetch_historical(self):
        async def run():
            await self.p.connect()
            start = time.time() - 3600
            end   = time.time()
            candles = await self.p.fetch_historical("AAPL", start, end, CandleInterval.M1)
            assert len(candles) > 0
            assert candles[0].is_complete
            await self.p.disconnect()
        _run(run())

    def test_health_check(self):
        async def run():
            await self.p.connect()
            h = await self.p.health_check()
            assert h.is_connected
            assert h.latency_ms >= 0
            await self.p.disconnect()
        _run(run())

    def test_get_stats(self):
        stats = self.p.get_stats()
        assert "provider_id" in stats

    def test_stream_quotes_yields_items(self):
        """Test that stream_quotes returns valid MarketQuote objects."""
        async def run():
            await self.p.connect()
            gen = self.p.stream_quotes(["AAPL"])
            quote = await gen.__anext__()
            assert isinstance(quote, MarketQuote)
            assert quote.symbol == "AAPL"
            await self.p.disconnect()
        _run(run())

    def test_stream_trades_yields_items(self):
        async def run():
            await self.p.connect()
            gen = self.p.stream_trades(["AAPL"])
            trade = await gen.__anext__()
            assert isinstance(trade, MarketTrade)
            await self.p.disconnect()
        _run(run())

    def test_stream_order_book_yields_items(self):
        async def run():
            await self.p.connect()
            gen = self.p.stream_order_book(["AAPL"])
            book = await gen.__anext__()
            assert isinstance(book, OrderBook)
            await self.p.disconnect()
        _run(run())


# ═════════════════════════════════════════════════════════════════════════════
# 6. Skeleton Providers
# ═════════════════════════════════════════════════════════════════════════════

class TestSkeletonProviders:
    def _check_skeleton(self, prov: BaseMarketDataProvider):
        assert prov.provider_id
        assert prov.capabilities is not None
        assert prov.metadata is not None

    def test_yahoo_finance(self):
        p = YahooFinanceProvider()
        self._check_skeleton(p)
        assert p.capabilities.supports_historical
        assert not p.capabilities.supports_streaming

    def test_nse_provider(self):
        p = NSEProvider()
        self._check_skeleton(p)
        assert p.capabilities.supports_streaming
        assert p.capabilities.requires_authentication

    def test_polygon_provider(self):
        p = PolygonProvider()
        self._check_skeleton(p)
        assert p.capabilities.supports_historical

    def test_alpha_vantage_provider(self):
        p = AlphaVantageProvider()
        self._check_skeleton(p)
        assert p.metadata.is_free  # free tier available

    def test_twelve_data_provider(self):
        p = TwelveDataProvider()
        self._check_skeleton(p)
        assert p.capabilities.supports_streaming

    def test_skeleton_raises_not_implemented(self):
        p = YahooFinanceProvider()
        async def run():
            await p.connect()
            with pytest.raises(NotImplementedError):
                await p.fetch_snapshot(["AAPL"])
        _run(run())

    def test_skeleton_connect_disconnect(self):
        async def run():
            p = NSEProvider()
            await p.connect()
            assert p.is_connected()
            await p.disconnect()
            assert not p.is_connected()
        _run(run())

    def test_alpha_vantage_connect_and_health(self):
        async def run():
            p = AlphaVantageProvider()
            await p.connect()
            h = await p.health_check()
            assert h.is_connected
            await p.disconnect()
        _run(run())


# ═════════════════════════════════════════════════════════════════════════════
# 7. Stream Buffer
# ═════════════════════════════════════════════════════════════════════════════

class TestStreamBuffer:
    def test_put_and_get(self):
        buf: StreamBuffer[int] = StreamBuffer(max_size=10)
        buf.put_nowait(42)
        assert _run(buf.get()) == 42

    def test_drop_on_full(self):
        buf: StreamBuffer[int] = StreamBuffer(max_size=3, drop_on_full=True)
        for i in range(5):
            buf.put_nowait(i)
        assert buf.qsize() <= 3
        assert buf.metrics.dropped > 0

    def test_raise_on_full(self):
        buf: StreamBuffer[int] = StreamBuffer(max_size=2, drop_on_full=False)
        buf.put_nowait(1)
        buf.put_nowait(2)
        with pytest.raises(StreamBufferOverflowError):
            buf.put_nowait(3)

    def test_metrics(self):
        buf: StreamBuffer[int] = StreamBuffer(max_size=100)
        for i in range(5):
            buf.put_nowait(i)
        assert buf.metrics.enqueued == 5
        assert buf.metrics.high_water >= 1

    def test_empty(self):
        buf: StreamBuffer[int] = StreamBuffer(max_size=10)
        assert buf.empty()

    def test_utilisation(self):
        buf: StreamBuffer[int] = StreamBuffer(max_size=10)
        for i in range(5):
            buf.put_nowait(i)
        assert buf.utilisation_pct() == pytest.approx(50.0)

    def test_repr(self):
        buf: StreamBuffer[str] = StreamBuffer(name="test_buf", max_size=10)
        assert "test_buf" in repr(buf)


# ═════════════════════════════════════════════════════════════════════════════
# 8. Subscription Manager
# ═════════════════════════════════════════════════════════════════════════════

class TestSubscriptionManager:
    def test_register_and_get(self):
        mgr = SubscriptionManager()
        rec = mgr.register("s1", "prov_a", ["AAPL"], [MarketDataType.QUOTE])
        assert rec.sub_id == "s1"
        assert mgr.get("s1").sub_id == "s1"

    def test_unregister(self):
        mgr = SubscriptionManager()
        mgr.register("s1", "prov_a", ["AAPL"], [MarketDataType.QUOTE])
        mgr.unregister("s1")
        with pytest.raises(SubscriptionNotFoundError):
            mgr.get("s1")

    def test_find_by_symbol(self):
        mgr = SubscriptionManager()
        mgr.register("s1", "prov_a", ["AAPL"], [MarketDataType.QUOTE])
        mgr.register("s2", "prov_a", ["GOOG"], [MarketDataType.QUOTE])
        results = mgr.find_by_symbol("AAPL")
        assert len(results) == 1
        assert results[0].sub_id == "s1"

    def test_find_by_provider(self):
        mgr = SubscriptionManager()
        mgr.register("s1", "prov_a", ["AAPL"], [MarketDataType.QUOTE])
        mgr.register("s2", "prov_b", ["GOOG"], [MarketDataType.QUOTE])
        results = mgr.find_by_provider("prov_a")
        assert len(results) == 1

    def test_capacity_exceeded(self):
        mgr = SubscriptionManager(max_subscriptions=2)
        mgr.register("s1", "p", ["A"], [MarketDataType.QUOTE])
        mgr.register("s2", "p", ["B"], [MarketDataType.QUOTE])
        with pytest.raises(SubscriptionCapacityError):
            mgr.register("s3", "p", ["C"], [MarketDataType.QUOTE])

    def test_count(self):
        mgr = SubscriptionManager()
        mgr.register("s1", "p", ["A"], [MarketDataType.QUOTE])
        assert mgr.count() == 1

    def test_record_event(self):
        mgr = SubscriptionManager()
        mgr.register("s1", "p", ["A"], [MarketDataType.QUOTE])
        mgr.record_event("s1")
        rec = mgr.get("s1")
        assert rec.event_count == 1

    def test_stats(self):
        mgr = SubscriptionManager()
        mgr.register("s1", "p", ["A"], [MarketDataType.QUOTE])
        s = mgr.stats()
        assert s["total"] == 1

    def test_unregister_nonexistent_raises(self):
        mgr = SubscriptionManager()
        with pytest.raises(SubscriptionNotFoundError):
            mgr.unregister("nonexistent")


# ═════════════════════════════════════════════════════════════════════════════
# 9. Stream Router
# ═════════════════════════════════════════════════════════════════════════════

class TestStreamRouter:
    def test_topic_route(self):
        router = StreamRouter()
        received = []
        router.subscribe_topic("NSE.AAPL.tick_received", "L1", received.append)
        event = MarketEvent(
            event_type=MarketEventType.TICK_RECEIVED,
            symbol="AAPL", exchange=Exchange.NSE,
            topic="NSE.AAPL.tick_received",
        )
        count = router.route(event)
        assert count == 1
        assert len(received) == 1

    def test_symbol_route(self):
        router = StreamRouter()
        received = []
        router.subscribe_symbol("GOOG", "L2", received.append)
        event = MarketEvent(symbol="GOOG")
        router.route(event)
        assert len(received) == 1

    def test_global_route(self):
        router = StreamRouter()
        received = []
        router.subscribe_all("L3", received.append)
        event = MarketEvent(symbol="ANY")
        router.route(event)
        assert len(received) == 1

    def test_unsubscribe(self):
        router = StreamRouter()
        received = []
        router.subscribe_all("L3", received.append)
        router.unsubscribe("L3")
        event = MarketEvent(symbol="ANY")
        router.route(event)
        assert len(received) == 0

    def test_no_route_counted(self):
        router = StreamRouter()
        event = MarketEvent(symbol="X", topic="exchange.X.event")
        router.route(event)
        assert router.stats()["no_route"] == 1

    def test_listener_count(self):
        router = StreamRouter()
        router.subscribe_all("G", lambda e: None)
        router.subscribe_symbol("X", "S", lambda e: None)
        assert router.listener_count() == 2


# ═════════════════════════════════════════════════════════════════════════════
# 10. Stream Dispatcher
# ═════════════════════════════════════════════════════════════════════════════

class TestStreamDispatcher:
    def test_register_and_dispatch(self):
        d = StreamDispatcher()
        sub = d.register(name="consumer_a")
        event = MarketEvent(symbol="X")
        sent = d.dispatch(event)
        assert sent == 1
        assert not sub.buffer.empty()

    def test_symbol_filter(self):
        d = StreamDispatcher()
        sub_aapl = d.register(symbols_filter=["AAPL"])
        sub_goog = d.register(symbols_filter=["GOOG"])
        d.dispatch(MarketEvent(symbol="AAPL"))
        assert not sub_aapl.buffer.empty()
        assert sub_goog.buffer.empty()

    def test_unregister(self):
        d = StreamDispatcher()
        sub = d.register()
        d.unregister(sub.sub_id)
        assert d.subscriber_count() == 0

    def test_stats(self):
        d = StreamDispatcher()
        d.register()
        d.dispatch(MarketEvent(symbol="X"))
        s = d.stats()
        assert s["dispatched"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# 11. Stream Manager
# ═════════════════════════════════════════════════════════════════════════════

class TestStreamManager:
    def test_create_and_remove_subscription(self):
        mgr = StreamManager()
        rec = mgr.create_subscription("prov", ["AAPL"], [MarketDataType.QUOTE])
        assert rec.sub_id
        mgr.remove_subscription(rec.sub_id)

    def test_ingest(self):
        mgr = StreamManager()
        received = []
        mgr.subscribe_all("all", received.append)
        event = MarketEvent(symbol="AAPL", source="test")
        mgr.ingest(event)
        assert len(received) == 1

    def test_register_consumer(self):
        mgr = StreamManager()
        consumer = mgr.register_consumer(symbols_filter=["GOOG"])
        event = MarketEvent(symbol="GOOG")
        mgr.ingest(event)
        assert not consumer.buffer.empty()

    def test_consumer_filter_blocks_other_symbols(self):
        mgr = StreamManager()
        consumer = mgr.register_consumer(symbols_filter=["AAPL"])
        mgr.ingest(MarketEvent(symbol="GOOG"))
        assert consumer.buffer.empty()

    def test_stats(self):
        mgr = StreamManager()
        mgr.ingest(MarketEvent(symbol="X", source="prov"))
        s = mgr.stats()
        assert s["events_ingested"] == 1

    def test_unregister_consumer(self):
        mgr = StreamManager()
        c = mgr.register_consumer()
        mgr.unregister_consumer(c.sub_id)
        assert mgr.dispatcher().subscriber_count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# 12. Validation — Gap Detector
# ═════════════════════════════════════════════════════════════════════════════

class TestGapDetector:
    def test_no_gap_first_record(self):
        g = GapDetector(max_gap_sec=10.0)
        t = MarketTick(symbol="X", timestamp=time.time())
        assert g.check_tick(t) is None

    def test_gap_detected(self):
        g = GapDetector(max_gap_sec=10.0)
        t1 = MarketTick(symbol="X", timestamp=1000.0)
        t2 = MarketTick(symbol="X", timestamp=1020.0)
        g.check_tick(t1)
        issue = g.check_tick(t2)
        assert issue is not None
        assert issue.anomaly_type == AnomalyType.GAP_IN_SERIES
        assert issue.value > 9.0

    def test_no_gap_within_threshold(self):
        g = GapDetector(max_gap_sec=60.0)
        t1 = MarketTick(symbol="X", timestamp=1000.0)
        t2 = MarketTick(symbol="X", timestamp=1010.0)
        g.check_tick(t1)
        assert g.check_tick(t2) is None

    def test_reset(self):
        g = GapDetector(max_gap_sec=5.0)
        t1 = MarketTick(symbol="X", timestamp=1000.0)
        t2 = MarketTick(symbol="X", timestamp=1020.0)
        g.check_tick(t1)
        g.reset("X")
        # After reset, t2 is a "first" record — no gap
        assert g.check_tick(t2) is None

    def test_stats(self):
        g = GapDetector()
        g.check_tick(MarketTick(symbol="X", timestamp=1000.0))
        g.check_tick(MarketTick(symbol="X", timestamp=1500.0))
        s = g.stats()
        assert s["gaps"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# 13. Validation — Duplicate Detector
# ═════════════════════════════════════════════════════════════════════════════

class TestDuplicateDetector:
    def test_no_dup_first(self):
        d = DuplicateDetector()
        t = MarketTick(symbol="X", timestamp=1000.0, price=100.0, size=1.0, sequence_no=1)
        assert d.check_tick(t) is None

    def test_duplicate_detected(self):
        d = DuplicateDetector()
        t = MarketTick(symbol="X", timestamp=1000.0, price=100.0, size=1.0, sequence_no=1)
        d.check_tick(t)
        issue = d.check_tick(t)   # same record
        assert issue is not None
        assert issue.anomaly_type == AnomalyType.DUPLICATE

    def test_trade_dedup_by_trade_id(self):
        d = DuplicateDetector()
        tr = MarketTrade(symbol="X", price=100.0, size=1.0, trade_id="tid1")
        assert d.check_trade(tr) is None
        assert d.check_trade(tr) is not None

    def test_candle_dedup(self):
        d = DuplicateDetector()
        c = MarketCandle(symbol="X", interval=CandleInterval.M1, timestamp=1000.0)
        assert d.check_candle(c) is None
        assert d.check_candle(c) is not None

    def test_stats(self):
        d = DuplicateDetector()
        t = MarketTick(symbol="X", timestamp=1.0, price=1.0, size=1.0, sequence_no=1)
        d.check_tick(t)
        d.check_tick(t)
        assert d.stats()["duplicates"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# 14. Validation — Anomaly Detector
# ═════════════════════════════════════════════════════════════════════════════

class TestAnomalyDetector:
    def test_zero_price(self):
        ad = AnomalyDetector()
        t = MarketTick(symbol="X", price=0.0, size=100.0)
        issues = ad.check_tick(t)
        assert any(i.anomaly_type == AnomalyType.ZERO_PRICE for i in issues)

    def test_negative_price(self):
        ad = AnomalyDetector()
        t = MarketTick(symbol="X", price=-1.0, size=100.0)
        issues = ad.check_tick(t)
        assert any(i.anomaly_type == AnomalyType.NEGATIVE_PRICE for i in issues)

    def test_inverted_spread(self):
        ad = AnomalyDetector()
        q = MarketQuote(symbol="X", bid=105.0, ask=100.0, mid=102.5)
        issues = ad.check_quote(q)
        assert any(i.anomaly_type == AnomalyType.SPREAD_INVERSION for i in issues)

    def test_bad_ohlc(self):
        ad = AnomalyDetector()
        c = MarketCandle(open=100, high=90, low=80, close=95)  # high < open
        issues = ad.check_candle(c)
        assert any(i.anomaly_type == AnomalyType.BAD_OHLC for i in issues)

    def test_no_anomaly_normal_price(self):
        ad = AnomalyDetector(warmup_periods=5)
        # Feed warmup data
        for i in range(10):
            t = MarketTick(symbol="X", price=100.0 + i * 0.01, size=100.0)
            ad.check_tick(t)
        # Normal price
        normal = MarketTick(symbol="X", price=100.05, size=100.0)
        issues = ad.check_tick(normal)
        assert not any(i.anomaly_type == AnomalyType.PRICE_SPIKE for i in issues)

    def test_stats(self):
        ad = AnomalyDetector()
        ad.check_tick(MarketTick(symbol="X", price=-1.0))  # negative price → anomaly counted
        s = ad.stats()
        assert s["checked"] >= 1


# ═════════════════════════════════════════════════════════════════════════════
# 15. MarketValidator
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketValidator:
    def test_validate_clean_quote(self):
        v = MarketValidator()
        q = MarketQuote(symbol="X", bid=100.0, ask=100.5, timestamp=time.time())
        issues = v.validate_quote(q)
        assert not any(i.severity == "error" for i in issues)

    def test_validate_stale_tick(self):
        v = MarketValidator(stale_threshold=1.0)
        t = MarketTick(symbol="X", price=100.0, timestamp=time.time())
        t.received_at = time.time() - 5.0   # 5s old
        issues = v.validate_tick(t)
        assert any(i.anomaly_type == AnomalyType.STALE_TIMESTAMP for i in issues)

    def test_validate_future_timestamp(self):
        v = MarketValidator(max_future_sec=1.0)
        t = MarketTick(symbol="X", price=100.0, timestamp=time.time() + 100.0)
        issues = v.validate_tick(t)
        assert any(i.anomaly_type == AnomalyType.FUTURE_TIMESTAMP for i in issues)

    def test_batch_report(self):
        v = MarketValidator()
        ticks = [MarketTick(symbol="X", price=100.0 + i, size=10.0, timestamp=time.time()) for i in range(5)]
        report = v.validate_ticks_batch(ticks)
        assert report.total_records == 5
        assert report.quality_score >= 0.0

    def test_stats(self):
        v = MarketValidator(provider_id="test_prov")
        v.validate_tick(MarketTick(symbol="X", price=100.0, timestamp=time.time()))
        s = v.stats()
        assert s["total_validated"] == 1
        assert s["provider_id"] == "test_prov"


# ═════════════════════════════════════════════════════════════════════════════
# 16. Quality Report
# ═════════════════════════════════════════════════════════════════════════════

class TestQualityReport:
    def test_compute_score_perfect(self):
        r = QualityReport(total_records=10, valid_records=10)
        score = r.compute_score()
        assert score == pytest.approx(1.0)

    def test_compute_score_partial(self):
        r = QualityReport(total_records=10, valid_records=8)
        score = r.compute_score()
        assert 0.7 < score <= 1.0

    def test_add_issue_anomaly(self):
        r = QualityReport()
        r.add_issue(QualityIssue(anomaly_type=AnomalyType.PRICE_SPIKE))
        assert r.anomaly_count == 1

    def test_add_issue_duplicate(self):
        r = QualityReport()
        r.add_issue(QualityIssue(anomaly_type=AnomalyType.DUPLICATE))
        assert r.duplicate_count == 1

    def test_is_acceptable(self):
        r = QualityReport(total_records=10, valid_records=10)
        r.compute_score()
        assert r.is_acceptable()

    def test_to_dict(self):
        r = QualityReport(provider_id="p", symbol="X")
        d = r.to_dict()
        assert "report_id" in d
        assert d["symbol"] == "X"


# ═════════════════════════════════════════════════════════════════════════════
# 17. Normalizer
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketNormalizer:
    def test_symbol_mapping(self):
        n = MarketNormalizer(symbol_map={"NIFTY50": "^NSEI"})
        t = MarketTick(symbol="NIFTY50", price=18000.0)
        n.normalize_tick(t)
        assert t.symbol == "^NSEI"

    def test_price_rounding(self):
        n = MarketNormalizer(price_dp=2)
        t = MarketTick(symbol="X", price=100.12345)
        n.normalize_tick(t)
        assert t.price == pytest.approx(100.12)

    def test_mid_fill_quote(self):
        n = MarketNormalizer()
        q = MarketQuote(symbol="X", bid=100.0, ask=100.4)
        n.normalize_quote(q)
        assert q.mid == pytest.approx(100.2)

    def test_change_fill_snapshot(self):
        n = MarketNormalizer()
        s = MarketSnapshot(symbol="X", last=110.0, prev_close=100.0, bid=109.0, ask=111.0)
        n.normalize_snapshot(s)
        assert s.change == pytest.approx(10.0)
        assert s.change_pct == pytest.approx(10.0)

    def test_normalize_candle(self):
        n = MarketNormalizer(price_dp=2)
        c = MarketCandle(symbol="X", open=100.1234, high=101.5678, low=99.2345, close=100.9876)
        n.normalize_candle(c)
        assert c.open == pytest.approx(100.12)

    def test_stats(self):
        n = MarketNormalizer()
        n.normalize_tick(MarketTick(symbol="X"))
        assert n.stats()["normalized_ticks"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# 18. Cache
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketDataCache:
    def test_put_and_get(self):
        c: MarketDataCache[int] = MarketDataCache(max_entries=100)
        c.put("k1", 42, ttl_sec=60.0)
        assert c.get("k1") == 42

    def test_miss(self):
        c: MarketDataCache[int] = MarketDataCache()
        assert c.get("nonexistent") is None

    def test_ttl_expiry(self):
        c: MarketDataCache[int] = MarketDataCache()
        c.put("k1", 99, ttl_sec=-1.0)   # already expired
        assert c.get("k1") is None

    def test_lru_eviction(self):
        c: MarketDataCache[str] = MarketDataCache(max_entries=3)
        c.put("a", "A"); c.put("b", "B"); c.put("c", "C")
        c.put("d", "D")   # evicts oldest
        assert c.size() <= 3

    def test_invalidate(self):
        c: MarketDataCache[int] = MarketDataCache()
        c.put("k1", 1)
        assert c.invalidate("k1")
        assert c.get("k1") is None

    def test_invalidate_prefix(self):
        c: MarketDataCache[int] = MarketDataCache()
        c.put("snap:AAPL", 1)
        c.put("snap:GOOG", 2)
        c.put("hist:AAPL", 3)
        removed = c.invalidate_prefix("snap:")
        assert removed == 2
        assert c.get("hist:AAPL") == 3

    def test_purge_expired(self):
        c: MarketDataCache[int] = MarketDataCache()
        c.put("k1", 1, ttl_sec=-1.0)
        c.put("k2", 2, ttl_sec=60.0)
        removed = c.purge_expired()
        assert removed == 1
        assert c.get("k2") == 2

    def test_stats(self):
        c: MarketDataCache[int] = MarketDataCache(name="test_cache")
        c.put("k", 1)
        c.get("k")
        c.get("nonexistent")
        s = c.stats()
        assert s["hits"] == 1
        assert s["misses"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# 19. Event Publisher
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketEventPublisher:
    def test_publish_increments_sequence(self):
        mgr = StreamManager()
        pub = MarketEventPublisher(mgr)
        event = MarketEvent(symbol="X")
        pub.publish(event)
        assert event.sequence_no == 1
        event2 = MarketEvent(symbol="Y")
        pub.publish(event2)
        assert event2.sequence_no == 2

    def test_publish_payload(self):
        received = []
        mgr = StreamManager()
        mgr.subscribe_all("L", received.append)
        pub = MarketEventPublisher(mgr)
        pub.publish_payload(
            payload    = MarketTick(symbol="X"),
            event_type = MarketEventType.TICK_RECEIVED,
            symbol     = "X",
            source     = "test_prov",
        )
        assert len(received) == 1

    def test_replay_flag(self):
        mgr = StreamManager()
        pub = MarketEventPublisher(mgr)
        event = MarketEvent(symbol="X", is_replay=True)
        pub.publish(event)
        assert pub.stats()["replayed"] == 1

    def test_stats(self):
        mgr = StreamManager()
        pub = MarketEventPublisher(mgr)
        pub.publish(MarketEvent(symbol="X"))
        s = pub.stats()
        assert s["published"] == 1
        assert s["sequence_no"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# 20. Market Data Registry
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketDataRegistry:
    def test_register_and_get(self):
        reg = MarketDataRegistry()
        p = PaperMarketProvider()
        reg.register(p)
        assert reg.get("paper_market") is p

    def test_duplicate_raises(self):
        reg = MarketDataRegistry()
        reg.register(PaperMarketProvider())
        with pytest.raises(MarketDataProviderAlreadyRegisteredError):
            reg.register(PaperMarketProvider())

    def test_capacity_limit(self):
        reg = MarketDataRegistry(max_providers=1)
        reg.register(PaperMarketProvider())
        with pytest.raises(MarketDataRegistryError):
            reg.register(YahooFinanceProvider())

    def test_unregister(self):
        reg = MarketDataRegistry()
        reg.register(PaperMarketProvider())
        reg.unregister("paper_market")
        with pytest.raises(MarketDataProviderNotFoundError):
            reg.get("paper_market")

    def test_find_for_data_type(self):
        reg = MarketDataRegistry()
        reg.register(PaperMarketProvider())
        results = reg.find_for_data_type(MarketDataType.SNAPSHOT)
        assert len(results) >= 1

    def test_find_for_exchange(self):
        reg = MarketDataRegistry()
        reg.register(PaperMarketProvider())   # supports GLOBAL
        results = reg.find_for_exchange(Exchange.NSE)
        assert len(results) >= 1

    def test_contains(self):
        reg = MarketDataRegistry()
        reg.register(PaperMarketProvider())
        assert reg.contains("paper_market")
        assert not reg.contains("unknown")

    def test_stats(self):
        reg = MarketDataRegistry()
        reg.register(PaperMarketProvider())
        s = reg.stats()
        assert s["total"] == 1

    def test_provider_ids(self):
        reg = MarketDataRegistry()
        reg.register(PaperMarketProvider())
        assert "paper_market" in reg.provider_ids()


# ═════════════════════════════════════════════════════════════════════════════
# 21. Market Data Context
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketDataContext:
    def test_set_and_get(self):
        MarketDataContextState.set("prov1", "AAPL", "subscribe")
        assert MarketDataContextState.get_provider_id() == "prov1"
        assert MarketDataContextState.get_symbol() == "AAPL"
        assert MarketDataContextState.get_operation() == "subscribe"
        MarketDataContextState.clear()

    def test_elapsed_ms(self):
        MarketDataContextState.set("prov1")
        time.sleep(0.01)
        assert MarketDataContextState.elapsed_ms() >= 5.0
        MarketDataContextState.clear()

    def test_context_manager(self):
        with market_data_context("prov2", "GOOG", "fetch"):
            assert MarketDataContextState.get_provider_id() == "prov2"
        assert MarketDataContextState.get_provider_id() is None

    def test_clear(self):
        MarketDataContextState.set("p")
        MarketDataContextState.clear()
        assert MarketDataContextState.get_provider_id() is None


# ═════════════════════════════════════════════════════════════════════════════
# 22. Market Data Factory
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketDataFactory:
    def test_create_paper(self):
        p = MarketDataFactory.create_paper_market_provider(seed=1)
        assert p.provider_id == "paper_market"

    def test_create_stream_manager(self):
        m = MarketDataFactory.create_stream_manager()
        assert isinstance(m, StreamManager)

    def test_create_validator(self):
        v = MarketDataFactory.create_market_validator(provider_id="test")
        assert isinstance(v, MarketValidator)

    def test_create_normalizer(self):
        n = MarketDataFactory.create_market_normalizer(symbol_map={"A": "B"})
        t = MarketTick(symbol="A")
        n.normalize_tick(t)
        assert t.symbol == "B"

    def test_create_cache(self):
        c = MarketDataFactory.create_cache(name="fc", max_entries=50)
        assert c.name == "fc"

    def test_create_monitor(self):
        m = MarketDataFactory.create_monitor(poll_interval_sec=10.0)
        assert isinstance(m, MarketDataMonitor)

    def test_create_historical(self):
        h = MarketDataFactory.create_historical_manager()
        assert isinstance(h, HistoricalDataManager)

    def test_create_publisher(self):
        sm = MarketDataFactory.create_stream_manager()
        pub = MarketDataFactory.create_publisher(sm)
        assert isinstance(pub, MarketEventPublisher)


# ═════════════════════════════════════════════════════════════════════════════
# 23. Historical Data Manager
# ═════════════════════════════════════════════════════════════════════════════

class TestHistoricalDataManager:
    def test_no_provider_raises(self):
        h = HistoricalDataManager()
        async def run():
            await h.fetch("AAPL", 0.0, time.time(), CandleInterval.D1)
        with pytest.raises(HistoricalDataNotAvailableError):
            _run(run())

    def test_fetch_with_paper_provider(self):
        h = HistoricalDataManager()
        p = PaperMarketProvider()
        async def run():
            await p.connect()
            h.register_provider(p)
            candles = await h.fetch("AAPL", time.time() - 3600, time.time(), CandleInterval.M1)
            assert len(candles) > 0
            await p.disconnect()
        _run(run())

    def test_unregister_provider(self):
        h = HistoricalDataManager()
        h.register_provider(PaperMarketProvider())
        h.unregister_provider("paper_market")
        assert "paper_market" not in h.provider_ids()


# ═════════════════════════════════════════════════════════════════════════════
# 24. Market Data Manager
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketDataManager:
    def _make_manager(self):
        registry   = MarketDataRegistry()
        sm         = MarketDataFactory.create_stream_manager()
        publisher  = MarketDataFactory.create_publisher(sm)
        normalizer = MarketDataFactory.create_market_normalizer()
        validator  = MarketDataFactory.create_market_validator()
        cache      = MarketDataFactory.create_cache()
        historical = MarketDataFactory.create_historical_manager()
        monitor    = MarketDataFactory.create_monitor()
        from iios.integration.market_data.market_data_manager import MarketDataManager
        return MarketDataManager(
            registry=registry, stream_manager=sm, publisher=publisher,
            normalizer=normalizer, validator=validator, cache=cache,
            historical=historical, monitor=monitor,
        )

    def test_register_provider(self):
        m = self._make_manager()
        m.register_provider(PaperMarketProvider())
        assert m._registry.count() == 1

    def test_no_provider_for_snapshot(self):
        m = self._make_manager()
        async def run():
            await m.fetch_snapshot(["AAPL"])
        with pytest.raises(NoProviderForSymbolError):
            _run(run())

    def test_fetch_snapshot_with_paper(self):
        m = self._make_manager()
        p = PaperMarketProvider()
        async def run():
            m.register_provider(p)
            await m.connect_provider("paper_market")
            snaps = await m.fetch_snapshot(["AAPL", "GOOG"], use_cache=False)
            assert len(snaps) == 2
            await m.disconnect_provider("paper_market")
        _run(run())

    def test_fetch_snapshot_uses_cache(self):
        m = self._make_manager()
        p = PaperMarketProvider()
        async def run():
            m.register_provider(p)
            await m.connect_provider("paper_market")
            _ = await m.fetch_snapshot(["AAPL"], use_cache=True)
            snaps2 = await m.fetch_snapshot(["AAPL"], use_cache=True)
            assert len(snaps2) >= 1
            await m.disconnect_provider("paper_market")
        _run(run())

    def test_subscribe_and_unsubscribe(self):
        m = self._make_manager()
        p = PaperMarketProvider()
        async def run():
            m.register_provider(p)
            await m.connect_provider("paper_market")
            handle = await m.subscribe(["AAPL"], [MarketDataType.QUOTE])
            assert handle.provider_id == "paper_market"
            await m.unsubscribe(handle)
            await m.disconnect_provider("paper_market")
        _run(run())

    def test_stats(self):
        m = self._make_manager()
        s = m.stats()
        assert "registry" in s
        assert "cache" in s


# ═════════════════════════════════════════════════════════════════════════════
# 25. Engine Lifecycle
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketDataEngine:
    def setup_method(self):
        reset_market_data_engine()

    def teardown_method(self):
        reset_market_data_engine()

    def test_start_and_stop(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            assert engine.is_running()
            assert engine.status() == MarketDataEngineStatus.RUNNING
            await engine.stop()
            assert not engine.is_running()
        _run(run())

    def test_double_start_raises(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            with pytest.raises(MarketDataEngineAlreadyRunningError):
                await engine.start()
            await engine.stop()
        _run(run())

    def test_operation_before_start_raises(self):
        engine = MarketDataEngine()
        with pytest.raises(MarketDataEngineNotRunningError):
            engine.register_provider(PaperMarketProvider())

    def test_register_provider(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            engine.register_provider(PaperMarketProvider())
            assert engine.registry().count() == 1
            await engine.stop()
        _run(run())

    def test_connect_provider(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            engine.register_provider(PaperMarketProvider())
            await engine.connect_provider("paper_market")
            assert engine.registry().get("paper_market").is_connected()
            await engine.stop()
        _run(run())

    def test_fetch_snapshot(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            engine.register_provider(PaperMarketProvider())
            await engine.connect_provider("paper_market")
            snaps = await engine.fetch_snapshot(["AAPL"])
            assert len(snaps) == 1
            assert snaps[0].symbol == "AAPL"
            await engine.stop()
        _run(run())

    def test_fetch_historical(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            engine.register_provider(PaperMarketProvider())
            await engine.connect_provider("paper_market")
            start = time.time() - 3600
            end   = time.time()
            candles = await engine.fetch_historical("AAPL", start, end, CandleInterval.M1)
            assert len(candles) > 0
            await engine.stop()
        _run(run())

    def test_subscribe(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            engine.register_provider(PaperMarketProvider())
            await engine.connect_provider("paper_market")
            handle = await engine.subscribe(["AAPL", "GOOG"], [MarketDataType.QUOTE])
            assert handle.handle_id
            await engine.unsubscribe(handle)
            await engine.stop()
        _run(run())

    def test_uptime_sec(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            time.sleep(0.05)
            assert engine.uptime_sec() >= 0.04
            await engine.stop()
        _run(run())

    def test_stats(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            s = engine.stats()
            assert s["status"] == MarketDataEngineStatus.RUNNING.value
            assert "manager" in s
            await engine.stop()
        _run(run())

    def test_stop_idempotent(self):
        async def run():
            engine = MarketDataEngine()
            await engine.start()
            await engine.stop()
            await engine.stop()   # second stop should be no-op
            assert not engine.is_running()
        _run(run())


# ═════════════════════════════════════════════════════════════════════════════
# 26. Singleton
# ═════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    def setup_method(self):
        reset_market_data_engine()

    def teardown_method(self):
        reset_market_data_engine()

    def test_same_instance(self):
        e1 = get_market_data_engine()
        e2 = get_market_data_engine()
        assert e1 is e2

    def test_reset_creates_new(self):
        e1 = get_market_data_engine()
        reset_market_data_engine()
        e2 = get_market_data_engine()
        assert e1 is not e2

    def test_singleton_not_running_initially(self):
        e = get_market_data_engine()
        assert not e.is_running()

    def test_accessors(self):
        async def run():
            e = MarketDataEngine()
            await e.start()
            assert e.manager()      is not None
            assert e.registry()     is not None
            assert e.stream_manager() is not None
            assert e.publisher()    is not None
            assert e.cache()        is not None
            assert e.monitor()      is not None
            await e.stop()
        _run(run())


# ═════════════════════════════════════════════════════════════════════════════
# 27. Monitor
# ═════════════════════════════════════════════════════════════════════════════

class TestMarketDataMonitor:
    def test_register_and_poll_health(self):
        async def run():
            mon = MarketDataMonitor(poll_interval_sec=999.0)
            p = PaperMarketProvider()
            await p.connect()
            mon.register_provider(p)
            await mon._poll_all()
            h = mon.get_health("paper_market")
            assert h is not None
            assert h.is_connected
            await p.disconnect()
        _run(run())

    def test_all_health(self):
        async def run():
            mon = MarketDataMonitor()
            p = PaperMarketProvider()
            await p.connect()
            mon.register_provider(p)
            await mon._poll_all()
            all_h = mon.all_health()
            assert "paper_market" in all_h
            await p.disconnect()
        _run(run())

    def test_unregister_removes_health(self):
        async def run():
            mon = MarketDataMonitor()
            p = PaperMarketProvider()
            mon.register_provider(p)
            mon.unregister_provider("paper_market")
            assert mon.get_health("paper_market") is None
        _run(run())

    def test_stats(self):
        mon = MarketDataMonitor()
        s = mon.stats()
        assert "provider_count" in s
