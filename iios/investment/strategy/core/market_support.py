"""iios/investment/strategy/core/market_support.py
Market and exchange support declarations for institutional strategies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet


class SupportedMarketType(str, Enum):
    """Broad market segment a strategy operates in."""
    EQUITY_CASH         = "equity_cash"
    EQUITY_DERIVATIVES  = "equity_derivatives"
    CURRENCY            = "currency"
    COMMODITY           = "commodity"
    DEBT                = "debt"
    CRYPTO              = "crypto"
    GLOBAL              = "global"


class SupportedExchangeZone(str, Enum):
    """Exchange or regional zone a strategy targets."""
    NSE    = "nse"
    BSE    = "bse"
    NYSE   = "nyse"
    NASDAQ = "nasdaq"
    LSE    = "lse"
    TSE    = "tse"
    GLOBAL = "global"


@dataclass(frozen=True)
class MarketSupport:
    """Declares which markets and exchanges an institutional strategy operates in."""
    market_types: FrozenSet[SupportedMarketType] = field(default_factory=frozenset)
    exchange_zones: FrozenSet[SupportedExchangeZone] = field(default_factory=frozenset)
    requires_premarket: bool = False
    requires_aftermarket: bool = False

    def supports_market(self, market: SupportedMarketType) -> bool:
        return market in self.market_types

    def supports_exchange(self, exchange: SupportedExchangeZone) -> bool:
        return exchange in self.exchange_zones

    def to_dict(self) -> dict:
        return {
            "market_types": sorted(m.value for m in self.market_types),
            "exchange_zones": sorted(e.value for e in self.exchange_zones),
            "requires_premarket": self.requires_premarket,
            "requires_aftermarket": self.requires_aftermarket,
        }

    @classmethod
    def indian_equity(cls) -> "MarketSupport":
        return cls(
            market_types=frozenset({
                SupportedMarketType.EQUITY_CASH,
                SupportedMarketType.EQUITY_DERIVATIVES,
            }),
            exchange_zones=frozenset({
                SupportedExchangeZone.NSE,
                SupportedExchangeZone.BSE,
            }),
        )

    @classmethod
    def global_all(cls) -> "MarketSupport":
        return cls(
            market_types=frozenset(SupportedMarketType),
            exchange_zones=frozenset(SupportedExchangeZone),
        )
