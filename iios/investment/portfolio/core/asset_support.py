"""iios/investment/portfolio/core/asset_support.py

Asset-class support matrix for the Institutional Portfolio Framework.
Defines which asset classes, exchanges, and currencies each portfolio domain
supports, and provides lookup utilities used by the framework and factory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Mapping

from iios.investment.portfolio.portfolio_constants import AssetClass
from iios.investment.portfolio.core.portfolio_types import PortfolioDomain


# ---------------------------------------------------------------------------
# Asset descriptors
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AssetDescriptor:
    """A single tradeable asset-class descriptor."""

    asset_class:   AssetClass
    display_name:  str
    exchanges:     FrozenSet[str]     = field(default_factory=frozenset)
    currencies:    FrozenSet[str]     = field(default_factory=frozenset)
    requires_cap:  FrozenSet[str]     = field(default_factory=frozenset)  # required capabilities

    def to_dict(self) -> dict:
        return {
            "asset_class":  self.asset_class.value,
            "display_name": self.display_name,
            "exchanges":    sorted(self.exchanges),
            "currencies":   sorted(self.currencies),
        }


# ---------------------------------------------------------------------------
# Canonical asset descriptors (authoritative source)
# ---------------------------------------------------------------------------

EQUITY_ASSET = AssetDescriptor(
    asset_class  = AssetClass.EQUITY,
    display_name = "Equity",
    exchanges    = frozenset({"NSE", "BSE", "NYSE", "NASDAQ", "LSE", "HKEx", "TSE"}),
    currencies   = frozenset({"INR", "USD", "GBP", "HKD", "JPY", "EUR"}),
)

DEBT_ASSET = AssetDescriptor(
    asset_class  = AssetClass.DEBT,
    display_name = "Fixed Income / Debt",
    exchanges    = frozenset({"NSE", "BSE", "NYSE", "LSE"}),
    currencies   = frozenset({"INR", "USD", "GBP", "EUR"}),
)

COMMODITY_ASSET = AssetDescriptor(
    asset_class  = AssetClass.COMMODITY,
    display_name = "Commodity",
    exchanges    = frozenset({"MCX", "NCDEX", "CME", "LME", "ICE"}),
    currencies   = frozenset({"INR", "USD"}),
)

CURRENCY_ASSET = AssetDescriptor(
    asset_class  = AssetClass.CURRENCY,
    display_name = "Forex / Currency",
    exchanges    = frozenset({"NSE-CDS", "LMAX", "FX-OTC"}),
    currencies   = frozenset({"INR", "USD", "EUR", "GBP", "JPY", "CHF", "AUD"}),
    requires_cap = frozenset({"multi_currency"}),
)

REAL_ESTATE_ASSET = AssetDescriptor(
    asset_class  = AssetClass.REAL_ESTATE,
    display_name = "Real Estate / REIT",
    exchanges    = frozenset({"NSE", "BSE", "NYSE"}),
    currencies   = frozenset({"INR", "USD"}),
)

DERIVATIVE_ASSET = AssetDescriptor(
    asset_class  = AssetClass.DERIVATIVE,
    display_name = "Derivatives (Options / Futures)",
    exchanges    = frozenset({"NSE-FO", "BSE-FO", "CME", "CBOE"}),
    currencies   = frozenset({"INR", "USD"}),
    requires_cap = frozenset({"derivatives"}),
)

CASH_ASSET = AssetDescriptor(
    asset_class  = AssetClass.CASH,
    display_name = "Cash & Equivalents",
    exchanges    = frozenset(),
    currencies   = frozenset({"INR", "USD", "EUR", "GBP", "JPY"}),
)

ALTERNATIVE_ASSET = AssetDescriptor(
    asset_class  = AssetClass.ALTERNATIVE,
    display_name = "Alternative (Crypto / PE / Hedge)",
    exchanges    = frozenset({"BINANCE", "COINBASE", "KRAKEN", "OTC"}),
    currencies   = frozenset({"INR", "USD", "USDT", "BTC", "ETH"}),
)

ALL_ASSET_DESCRIPTORS: tuple[AssetDescriptor, ...] = (
    EQUITY_ASSET, DEBT_ASSET, COMMODITY_ASSET, CURRENCY_ASSET,
    REAL_ESTATE_ASSET, DERIVATIVE_ASSET, CASH_ASSET, ALTERNATIVE_ASSET,
)

_DESCRIPTOR_MAP: dict[AssetClass, AssetDescriptor] = {
    d.asset_class: d for d in ALL_ASSET_DESCRIPTORS
}


def get_asset_descriptor(asset_class: AssetClass) -> AssetDescriptor:
    """Return the canonical descriptor for an asset class."""
    if asset_class not in _DESCRIPTOR_MAP:
        raise KeyError(f"No descriptor registered for asset class: {asset_class!r}")
    return _DESCRIPTOR_MAP[asset_class]


# ---------------------------------------------------------------------------
# Support matrix — which asset classes each domain supports
# ---------------------------------------------------------------------------

_DOMAIN_SUPPORT: Mapping[PortfolioDomain, FrozenSet[AssetClass]] = {
    PortfolioDomain.LONG_TERM: frozenset({
        AssetClass.EQUITY, AssetClass.DEBT, AssetClass.REAL_ESTATE,
        AssetClass.CASH, AssetClass.ALTERNATIVE,
    }),
    PortfolioDomain.SWING: frozenset({
        AssetClass.EQUITY, AssetClass.DERIVATIVE, AssetClass.CASH,
    }),
    PortfolioDomain.INTRADAY: frozenset({
        AssetClass.EQUITY, AssetClass.DERIVATIVE, AssetClass.CURRENCY, AssetClass.CASH,
    }),
    PortfolioDomain.ETF: frozenset({
        AssetClass.EQUITY, AssetClass.DEBT, AssetClass.COMMODITY,
        AssetClass.REAL_ESTATE, AssetClass.CASH,
    }),
    PortfolioDomain.DIVIDEND: frozenset({
        AssetClass.EQUITY, AssetClass.DEBT, AssetClass.REAL_ESTATE, AssetClass.CASH,
    }),
    PortfolioDomain.OPTIONS: frozenset({
        AssetClass.DERIVATIVE, AssetClass.CASH,
    }),
    PortfolioDomain.FUTURES: frozenset({
        AssetClass.DERIVATIVE, AssetClass.COMMODITY, AssetClass.CURRENCY, AssetClass.CASH,
    }),
    PortfolioDomain.CRYPTO: frozenset({
        AssetClass.ALTERNATIVE, AssetClass.CASH,
    }),
    PortfolioDomain.MULTI_ASSET: frozenset({
        AssetClass.EQUITY, AssetClass.DEBT, AssetClass.COMMODITY, AssetClass.CURRENCY,
        AssetClass.REAL_ESTATE, AssetClass.DERIVATIVE, AssetClass.CASH,
        AssetClass.ALTERNATIVE,
    }),
    PortfolioDomain.CUSTOM: frozenset(set(AssetClass)),
}


class AssetSupportMatrix:
    """
    Immutable lookup table: PortfolioDomain → FrozenSet[AssetClass].
    Used by the factory and validator to gate portfolio construction.
    """

    def __init__(self) -> None:
        self._matrix = dict(_DOMAIN_SUPPORT)

    def supported_assets(self, domain: PortfolioDomain) -> FrozenSet[AssetClass]:
        return self._matrix.get(domain, frozenset())

    def supports(self, domain: PortfolioDomain, asset_class: AssetClass) -> bool:
        return asset_class in self.supported_assets(domain)

    def domains_for_asset(self, asset_class: AssetClass) -> list[PortfolioDomain]:
        return [d for d, assets in self._matrix.items() if asset_class in assets]

    def to_dict(self) -> dict:
        return {
            d.value: [a.value for a in sorted(assets, key=lambda x: x.value)]
            for d, assets in self._matrix.items()
        }


# Shared singleton — created once, never mutated
ASSET_SUPPORT_MATRIX = AssetSupportMatrix()
