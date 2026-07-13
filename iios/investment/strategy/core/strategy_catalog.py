"""iios/investment/strategy/core/strategy_catalog.py
Searchable catalog over the institutional strategy registry.
"""
from __future__ import annotations

from typing import List, Optional

from .asset_support import SupportedAssetClass
from .market_support import SupportedMarketType
from .strategy_capabilities import StrategyCapability
from .strategy_descriptor import StrategyDescriptor
from .strategy_registry import InstitutionalStrategyRegistry
from .timeframe_support import TradingStyle


class InstitutionalStrategyCatalog:
    """
    Read-only search and discovery interface over InstitutionalStrategyRegistry.
    All filter parameters are optional; unset filters are not applied.
    """

    def __init__(self, registry: InstitutionalStrategyRegistry) -> None:
        self._registry = registry

    def search(
        self,
        asset_class: Optional[SupportedAssetClass] = None,
        market_type: Optional[SupportedMarketType] = None,
        style: Optional[TradingStyle] = None,
        capability: Optional[StrategyCapability] = None,
        tag: Optional[str] = None,
        include_experimental: bool = False,
        include_deprecated: bool = False,
        enabled_only: bool = True,
    ) -> List[StrategyDescriptor]:
        """Return descriptors for all strategies matching all provided filters."""
        results = []
        for desc in self._registry.all_descriptors():
            if enabled_only and not self._registry.is_enabled(desc.strategy_id):
                continue
            if not include_experimental and desc.is_experimental:
                continue
            if not include_deprecated and desc.is_deprecated:
                continue
            if asset_class and not desc.supports_asset(asset_class):
                continue
            if market_type and not desc.supports_market(market_type):
                continue
            if style and not desc.supports_style(style):
                continue
            if capability and not desc.has_capability(capability):
                continue
            if tag and tag not in desc.tags:
                continue
            results.append(desc)
        return results

    def get(self, strategy_id: str) -> Optional[StrategyDescriptor]:
        return self._registry.get_descriptor(strategy_id)

    def all(self, include_deprecated: bool = False) -> List[StrategyDescriptor]:
        return self.search(
            include_experimental=True,
            include_deprecated=include_deprecated,
            enabled_only=False,
        )

    def by_tag(self, tag: str) -> List[StrategyDescriptor]:
        return self.search(tag=tag, include_experimental=True, enabled_only=False)

    def by_asset(self, asset: SupportedAssetClass) -> List[StrategyDescriptor]:
        return self.search(asset_class=asset)

    def by_style(self, style: TradingStyle) -> List[StrategyDescriptor]:
        return self.search(style=style)

    def by_capability(self, cap: StrategyCapability) -> List[StrategyDescriptor]:
        return self.search(capability=cap)

    def count(self) -> int:
        return len(self.all())

    def strategy_ids(self) -> List[str]:
        return [d.strategy_id for d in self.all()]
