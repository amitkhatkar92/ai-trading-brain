"""
iios/observation/collectors/categories/base_category.py
=======================================================
Category-specific abstract base collectors.

These ABCs define the typed interface each vendor integration must satisfy.
Only the framework and interface are defined here — no vendor code.

Collector Categories
--------------------
MarketDataCollector       — OHLCV, tick data, quotes
NewsCollector             — news articles, press releases
MacroCollector            — GDP, CPI, interest rates, FX
CorporateActionCollector  — dividends, splits, buybacks
FinancialStatementCollector — P&L, balance sheet, cash flow
ExchangeCollector         — order book, trades, circuit breakers
BrokerCollector           — positions, orders, PnL from broker
AlternativeDataCollector  — satellite, credit card, IoT data
SocialMediaCollector      — Twitter, Reddit, StockTwits sentiment
ResearchCollector         — analyst reports, research notes
InternalSystemCollector   — IIOS internal metrics and events
PluginCollector           — third-party plugin extensibility point
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Optional

from ..base_collector     import BaseCollector, CollectorConfig
from ..collector_constants import CollectorCategory
from ...observation_constants import ObservationSource, ObservationType
from ...models.observation import Observation

__all__ = [
    "MarketDataCollector",
    "NewsCollector",
    "MacroCollector",
    "CorporateActionCollector",
    "FinancialStatementCollector",
    "ExchangeCollector",
    "BrokerCollector",
    "AlternativeDataCollector",
    "SocialMediaCollector",
    "ResearchCollector",
    "InternalSystemCollector",
    "PluginCollector",
]


class MarketDataCollector(BaseCollector):
    """
    Abstract base for market data collectors (OHLCV, ticks, quotes).

    Concrete implementations: DhanFeedCollector, YFinanceCollector, …
    """
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.MARKET_DATA
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...

    def get_quote(self, symbol: str) -> Optional[dict[str, Any]]:
        """Return the latest quote for *symbol*. Override in concrete class."""
        return None

    def get_history(
        self,
        symbol: str,
        days:   int = 30,
    ) -> list[dict[str, Any]]:
        """Return historical OHLCV bars. Override in concrete class."""
        return []


class NewsCollector(BaseCollector):
    """Abstract base for news and press-release collectors."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.NEWS
        config.obs_type = ObservationType.NEWS
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class MacroCollector(BaseCollector):
    """Abstract base for macroeconomic data collectors."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.MACRO
        config.obs_type = ObservationType.ECONOMIC
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class CorporateActionCollector(BaseCollector):
    """Abstract base for corporate action collectors."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.CORPORATE
        config.obs_type = ObservationType.CORPORATE_ACTION
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class FinancialStatementCollector(BaseCollector):
    """Abstract base for financial statement collectors."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.FINANCIAL
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class ExchangeCollector(BaseCollector):
    """Abstract base for exchange data collectors (order book, trades)."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.EXCHANGE
        config.obs_type = ObservationType.MARKET_DATA
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class BrokerCollector(BaseCollector):
    """Abstract base for broker data collectors (positions, orders, PnL)."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.BROKER
        config.obs_type = ObservationType.ORDER_EVENT
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class AlternativeDataCollector(BaseCollector):
    """Abstract base for alternative data collectors."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.ALTERNATIVE
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class SocialMediaCollector(BaseCollector):
    """Abstract base for social media data collectors."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.SOCIAL
        config.obs_type = ObservationType.SOCIAL
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class ResearchCollector(BaseCollector):
    """Abstract base for research report collectors."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.RESEARCH
        config.obs_type = ObservationType.RESEARCH
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class InternalSystemCollector(BaseCollector):
    """Abstract base for internal IIOS metrics and event collectors."""
    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.INTERNAL
        config.obs_type = ObservationType.SYSTEM_EVENT
        config.source   = ObservationSource.INTERNAL_AGENT
        super().__init__(config)

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...


class PluginCollector(BaseCollector):
    """
    Extensibility base for third-party plugin collectors.

    Plugin authors subclass this and override ``PLUGIN_NAME``,
    ``PLUGIN_VERSION``, ``_do_collect()``, and ``_do_normalise()``.
    """
    PLUGIN_NAME:    str = "unnamed_plugin"
    PLUGIN_VERSION: str = "1.0.0"
    PLUGIN_AUTHOR:  str = ""

    def __init__(self, config: CollectorConfig) -> None:
        config.category = CollectorCategory.PLUGIN
        super().__init__(config)

    def plugin_info(self) -> dict[str, str]:
        return {
            "name":    self.PLUGIN_NAME,
            "version": self.PLUGIN_VERSION,
            "author":  self.PLUGIN_AUTHOR,
            "class":   type(self).__name__,
        }

    @abstractmethod
    def _do_collect(self) -> Any: ...

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]: ...
