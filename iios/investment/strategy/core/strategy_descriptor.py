"""iios/investment/strategy/core/strategy_descriptor.py
Immutable institutional strategy descriptor — capabilities, version, and constraints.

Named StrategyDescriptor to avoid collision with the mutable StrategyMetadata
that already lives in this package (core/strategy_metadata.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import FrozenSet, Tuple

from .asset_support import AssetSupport, SupportedAssetClass
from .market_support import MarketSupport, SupportedExchangeZone, SupportedMarketType
from .strategy_capabilities import StrategyCapability
from .timeframe_support import TimeframeSupport, TradingStyle


@dataclass(frozen=True)
class StrategyVersion:
    """Semantic version tuple."""
    major: int = 1
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: "StrategyVersion") -> bool:
        """Same major version = backward compatible."""
        return self.major == other.major

    @classmethod
    def from_string(cls, s: str) -> "StrategyVersion":
        parts = (s or "1.0.0").split(".")
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 1,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
        )


@dataclass(frozen=True)
class StrategyDescriptor:
    """
    Immutable, capability-rich descriptor for an institutional strategy.

    Every strategy registered in the institutional framework must declare
    a StrategyDescriptor. It is the authoritative source of:
      - Identity (strategy_id, name, version)
      - Capabilities (what it can do)
      - Support matrix (assets, markets, timeframes)
      - Constraints (capital, positions)
      - Lineage (author, tags, dependencies)
    """
    strategy_id: str
    name: str
    version: StrategyVersion = field(default_factory=StrategyVersion)
    author: str = "IIOS"
    description: str = ""

    capabilities: FrozenSet[StrategyCapability] = field(default_factory=frozenset)
    asset_support: AssetSupport = field(default_factory=AssetSupport.equity_only)
    market_support: MarketSupport = field(default_factory=MarketSupport.indian_equity)
    timeframe_support: TimeframeSupport = field(default_factory=TimeframeSupport.intraday)

    dependencies: Tuple[str, ...] = ()       # other strategy_ids this depends on
    tags: Tuple[str, ...] = ()

    min_capital: float = 0.0
    max_concurrent_positions: int = 1
    min_universe_size: int = 1

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    is_experimental: bool = False
    is_deprecated: bool = False

    # ── Capability queries ─────────────────────────────────────────────────

    def has_capability(self, cap: StrategyCapability) -> bool:
        return cap in self.capabilities

    def supports_asset(self, asset: SupportedAssetClass) -> bool:
        return self.asset_support.supports(asset)

    def supports_market(self, market: SupportedMarketType) -> bool:
        return self.market_support.supports_market(market)

    def supports_exchange(self, exchange: SupportedExchangeZone) -> bool:
        return self.market_support.supports_exchange(exchange)

    def supports_style(self, style: TradingStyle) -> bool:
        return self.timeframe_support.supports_style(style)

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": str(self.version),
            "author": self.author,
            "description": self.description,
            "capabilities": sorted(c.value for c in self.capabilities),
            "asset_support": self.asset_support.to_dict(),
            "market_support": self.market_support.to_dict(),
            "timeframe_support": self.timeframe_support.to_dict(),
            "dependencies": list(self.dependencies),
            "tags": list(self.tags),
            "min_capital": self.min_capital,
            "max_concurrent_positions": self.max_concurrent_positions,
            "is_experimental": self.is_experimental,
            "is_deprecated": self.is_deprecated,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
