"""iios/integration/market_data/market_data_factory.py

Factory for creating pre-wired provider and component instances.
"""
from __future__ import annotations

from typing import Any

from iios.integration.market_data.cache.market_data_cache              import MarketDataCache
from iios.integration.market_data.distribution.market_event_publisher  import MarketEventPublisher
from iios.integration.market_data.historical.historical_data_manager   import HistoricalDataManager
from iios.integration.market_data.monitoring.market_data_monitor       import MarketDataMonitor
from iios.integration.market_data.normalization.market_normalizer      import MarketNormalizer
from iios.integration.market_data.providers.alpha_vantage_provider     import AlphaVantageProvider
from iios.integration.market_data.providers.nse_provider               import NSEProvider
from iios.integration.market_data.providers.paper_market_provider      import PaperMarketProvider
from iios.integration.market_data.providers.polygon_provider           import PolygonProvider
from iios.integration.market_data.providers.twelve_data_provider       import TwelveDataProvider
from iios.integration.market_data.providers.yahoo_finance_provider     import YahooFinanceProvider
from iios.integration.market_data.streaming.stream_manager             import StreamManager
from iios.integration.market_data.validation.market_validator          import MarketValidator


class MarketDataFactory:
    """
    Creates instances of all Market Data Framework components.

    All factory methods return new instances.  Wire-up and singleton
    management is done by MarketDataEngine.
    """

    # ── Providers ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_yahoo_finance_provider() -> YahooFinanceProvider:
        return YahooFinanceProvider()

    @staticmethod
    def create_nse_provider() -> NSEProvider:
        return NSEProvider()

    @staticmethod
    def create_polygon_provider() -> PolygonProvider:
        return PolygonProvider()

    @staticmethod
    def create_alpha_vantage_provider() -> AlphaVantageProvider:
        return AlphaVantageProvider()

    @staticmethod
    def create_twelve_data_provider() -> TwelveDataProvider:
        return TwelveDataProvider()

    @staticmethod
    def create_paper_market_provider(
        seed: int = 42, tick_interval_sec: float = 0.1
    ) -> PaperMarketProvider:
        return PaperMarketProvider(seed=seed, tick_interval_sec=tick_interval_sec)

    # ── Infrastructure ────────────────────────────────────────────────────────

    @staticmethod
    def create_stream_manager(heartbeat_interval_sec: float = 30.0) -> StreamManager:
        return StreamManager(heartbeat_interval_sec=heartbeat_interval_sec)

    @staticmethod
    def create_market_validator(
        provider_id: str = "", max_gap_sec: float = 300.0
    ) -> MarketValidator:
        return MarketValidator(provider_id=provider_id, max_gap_sec=max_gap_sec)

    @staticmethod
    def create_market_normalizer(
        symbol_map: dict[str, str] | None = None,
    ) -> MarketNormalizer:
        return MarketNormalizer(symbol_map=symbol_map)

    @staticmethod
    def create_cache(
        name: str = "market_data", max_entries: int = 100_000, default_ttl: float = 10.0
    ) -> MarketDataCache[Any]:
        return MarketDataCache(max_entries=max_entries, default_ttl=default_ttl, name=name)

    @staticmethod
    def create_historical_manager() -> HistoricalDataManager:
        return HistoricalDataManager()

    @staticmethod
    def create_monitor(poll_interval_sec: float = 30.0) -> MarketDataMonitor:
        return MarketDataMonitor(poll_interval_sec=poll_interval_sec)

    @staticmethod
    def create_publisher(stream_manager: StreamManager) -> MarketEventPublisher:
        return MarketEventPublisher(stream_manager=stream_manager)
