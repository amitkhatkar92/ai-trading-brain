"""iios/investment/strategy/core/asset_support.py
Asset class support declarations for institutional strategies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet


class SupportedAssetClass(str, Enum):
    """Asset classes an institutional strategy may target."""
    EQUITY      = "equity"
    ETF         = "etf"
    OPTIONS     = "options"
    FUTURES     = "futures"
    FOREX       = "forex"
    CRYPTO      = "crypto"
    COMMODITY   = "commodity"
    BOND        = "bond"
    INDEX       = "index"
    MULTI_ASSET = "multi_asset"


ALL_ASSET_CLASSES: FrozenSet[SupportedAssetClass] = frozenset(SupportedAssetClass)


@dataclass(frozen=True)
class AssetSupport:
    """Declares which asset classes an institutional strategy supports."""
    supported: FrozenSet[SupportedAssetClass] = field(default_factory=frozenset)

    def supports(self, asset: SupportedAssetClass) -> bool:
        return asset in self.supported

    def is_multi_asset(self) -> bool:
        return len(self.supported) > 1 or SupportedAssetClass.MULTI_ASSET in self.supported

    def to_dict(self) -> dict:
        return {"supported": sorted(a.value for a in self.supported)}

    @classmethod
    def equity_only(cls) -> "AssetSupport":
        return cls(supported=frozenset({SupportedAssetClass.EQUITY}))

    @classmethod
    def equity_and_options(cls) -> "AssetSupport":
        return cls(supported=frozenset({SupportedAssetClass.EQUITY, SupportedAssetClass.OPTIONS}))

    @classmethod
    def all_assets(cls) -> "AssetSupport":
        return cls(supported=ALL_ASSET_CLASSES)
