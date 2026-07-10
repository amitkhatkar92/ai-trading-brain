"""iios/integration/market_data/historical/historical_data_manager.py

Coordinates historical data requests across multiple providers.
"""
from __future__ import annotations

import logging
from typing import Any

from iios.integration.market_data.core.market_candle         import MarketCandle
from iios.integration.market_data.market_data_constants      import CandleInterval
from iios.integration.market_data.market_data_exceptions      import (
    HistoricalDataNotAvailableError,
    MarketDataProviderNotFoundError,
)

logger = logging.getLogger(__name__)


class HistoricalDataManager:
    """
    Manages historical data retrieval across multiple registered providers.

    Providers that support historical data (``capabilities.supports_historical``)
    are tried in priority order.  Results may be cached by the caller.
    """

    def __init__(self) -> None:
        # Filled by MarketDataRegistry
        self._providers: dict[str, Any] = {}   # provider_id → BaseMarketDataProvider

    def register_provider(self, provider: Any) -> None:
        self._providers[provider.provider_id] = provider

    def unregister_provider(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)

    async def fetch(
        self,
        symbol:      str,
        start:       float,
        end:         float,
        interval:    CandleInterval,
        provider_id: str | None = None,
    ) -> list[MarketCandle]:
        """
        Fetch historical candles.

        If ``provider_id`` is given, only that provider is tried.
        Otherwise, the first provider that supports historical data and
        the requested interval is used.
        """
        if provider_id:
            prov = self._providers.get(provider_id)
            if prov is None:
                raise MarketDataProviderNotFoundError(
                    f"Provider '{provider_id}' not registered."
                )
            return await prov.fetch_historical(symbol, start, end, interval)

        # Auto-select
        for prov in self._providers.values():
            caps = prov.capabilities
            if caps.supports_historical and caps.supports_interval(interval):
                try:
                    return await prov.fetch_historical(symbol, start, end, interval)
                except NotImplementedError:
                    continue
                except Exception as exc:
                    logger.warning("[HistoricalDataManager] %s failed: %s", prov.provider_id, exc)

        raise HistoricalDataNotAvailableError(
            f"No provider can supply {interval.value} data for {symbol}."
        )

    def provider_ids(self) -> list[str]:
        return list(self._providers.keys())
