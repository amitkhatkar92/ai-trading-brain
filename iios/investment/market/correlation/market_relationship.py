"""iios/investment/market/correlation/market_relationship.py
Canonical intermarket relationship definitions and helpers.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from iios.investment.market.correlation.models import AssetClass, RelationshipType

# (asset_class_a, asset_class_b) -> (expected_type, description)
_CANONICAL: Dict[Tuple[str, str], Tuple[RelationshipType, str]] = {
    (AssetClass.EQUITY.value,        AssetClass.BOND.value):
        (RelationshipType.INVERSE, "Flight to bonds during equity selloffs"),
    (AssetClass.INDEX.value,         AssetClass.BOND.value):
        (RelationshipType.INVERSE, "Index declines drive bond rallies"),
    (AssetClass.EQUITY.value,        AssetClass.VOLATILITY.value):
        (RelationshipType.INVERSE, "VIX spikes on equity declines"),
    (AssetClass.INDEX.value,         AssetClass.VOLATILITY.value):
        (RelationshipType.INVERSE, "VIX inversely related to index"),
    (AssetClass.EQUITY.value,        AssetClass.PRECIOUS_METAL.value):
        (RelationshipType.INVERSE, "Gold rallies in equity risk-off"),
    (AssetClass.INDEX.value,         AssetClass.PRECIOUS_METAL.value):
        (RelationshipType.INVERSE, "Gold rallies when index declines"),
    (AssetClass.BOND.value,          AssetClass.VOLATILITY.value):
        (RelationshipType.POSITIVE, "Both bonds and VIX rise in fear"),
    (AssetClass.BOND.value,          AssetClass.PRECIOUS_METAL.value):
        (RelationshipType.POSITIVE, "Both as safe-haven assets"),
    (AssetClass.CURRENCY.value,      AssetClass.COMMODITY.value):
        (RelationshipType.INVERSE, "Strong dollar depresses commodity prices"),
    (AssetClass.CURRENCY.value,      AssetClass.PRECIOUS_METAL.value):
        (RelationshipType.INVERSE, "Strong dollar pressures gold"),
    (AssetClass.CRYPTO.value,        AssetClass.EQUITY.value):
        (RelationshipType.POSITIVE, "Crypto moves with risk-on sentiment"),
    (AssetClass.INTEREST_RATE.value, AssetClass.BOND.value):
        (RelationshipType.INVERSE, "Rising rates depress bond prices"),
    (AssetClass.COMMODITY.value,     AssetClass.EQUITY.value):
        (RelationshipType.POSITIVE, "Commodity demand tracks economic growth"),
    (AssetClass.SECTOR_ETF.value,    AssetClass.INDEX.value):
        (RelationshipType.POSITIVE, "Sectors broadly track the index"),
    (AssetClass.EQUITY.value,        AssetClass.EQUITY.value):
        (RelationshipType.POSITIVE, "Equities move together in the same market"),
    (AssetClass.INDEX.value,         AssetClass.INDEX.value):
        (RelationshipType.POSITIVE, "Indices are broadly correlated"),
}


def _get_canonical_entry(
    asset_class_a: str, asset_class_b: str,
) -> Tuple[RelationshipType, str]:
    key = (asset_class_a, asset_class_b)
    if key in _CANONICAL:
        return _CANONICAL[key]
    rev = (asset_class_b, asset_class_a)
    if rev in _CANONICAL:
        return _CANONICAL[rev]
    return RelationshipType.UNKNOWN, "No canonical relationship defined"


def get_expected_relationship(
    asset_class_a: str, asset_class_b: str,
) -> RelationshipType:
    """Return the expected RelationshipType for an asset-class pair."""
    return _get_canonical_entry(asset_class_a, asset_class_b)[0]


class MarketRelationshipTable:
    """Lookup table of canonical intermarket relationships."""

    def get(self, asset_class_a: str, asset_class_b: str) -> RelationshipType:
        return get_expected_relationship(asset_class_a, asset_class_b)

    def get_with_description(
        self, asset_class_a: str, asset_class_b: str
    ) -> Tuple[RelationshipType, str]:
        return _get_canonical_entry(asset_class_a, asset_class_b)

    def all_pairs(self) -> List[Tuple[str, str, RelationshipType]]:
        return [(k[0], k[1], v[0]) for k, v in _CANONICAL.items()]


def is_typical_correlation(
    asset_class_a: str, asset_class_b: str,
    correlation: float, threshold: float = 0.20,
) -> bool:
    expected = get_expected_relationship(asset_class_a, asset_class_b)
    if expected == RelationshipType.POSITIVE:
        return correlation >= -threshold
    if expected == RelationshipType.INVERSE:
        return correlation <= threshold
    return True


def anomaly_score(
    asset_class_a: str, asset_class_b: str, correlation: float,
) -> float:
    expected = get_expected_relationship(asset_class_a, asset_class_b)
    if expected == RelationshipType.POSITIVE:
        return max(0.0, (-correlation + 0.3) / 1.3)
    if expected == RelationshipType.INVERSE:
        return max(0.0, (correlation + 0.3) / 1.3)
    return 0.0


_EQUITY_LIKE = frozenset({
    AssetClass.EQUITY.value, AssetClass.INDEX.value, AssetClass.SECTOR_ETF.value
})
_SAFE_HAVENS = frozenset({
    AssetClass.BOND.value, AssetClass.PRECIOUS_METAL.value
})


def is_risk_on_pattern(
    asset_class_a: str, asset_class_b: str, correlation: float,
) -> bool:
    """True if this pair correlation indicates a risk-on regime."""
    if asset_class_a in _EQUITY_LIKE and asset_class_b in _EQUITY_LIKE:
        return correlation > 0.50
    if asset_class_a in _EQUITY_LIKE and asset_class_b == AssetClass.VOLATILITY.value:
        return correlation < -0.40
    if asset_class_b in _EQUITY_LIKE and asset_class_a == AssetClass.VOLATILITY.value:
        return correlation < -0.40
    return False


def is_risk_off_pattern(
    asset_class_a: str, asset_class_b: str, correlation: float,
) -> bool:
    """True if this pair correlation indicates a risk-off regime."""
    if asset_class_a in _EQUITY_LIKE and asset_class_b in _SAFE_HAVENS:
        return correlation < -0.30
    if asset_class_b in _EQUITY_LIKE and asset_class_a in _SAFE_HAVENS:
        return correlation < -0.30
    return False


def is_flight_to_safety(
    asset_class_a: str, asset_class_b: str, correlation: float,
) -> bool:
    """True if this pair shows a flight-to-safety pattern."""
    if asset_class_a in _EQUITY_LIKE and asset_class_b in _SAFE_HAVENS:
        return correlation < -0.50
    if asset_class_b in _EQUITY_LIKE and asset_class_a in _SAFE_HAVENS:
        return correlation < -0.50
    return False


def _triple_risk_on(
    equity_bond_corr: Optional[float],
    equity_vol_corr: Optional[float],
    equity_gold_corr: Optional[float],
) -> bool:
    signals = 0
    if equity_bond_corr is not None and equity_bond_corr > 0.10:
        signals += 1
    if equity_vol_corr is not None and equity_vol_corr < -0.40:
        signals += 1
    if equity_gold_corr is not None and equity_gold_corr > -0.10:
        signals += 1
    return signals >= 2


def _triple_risk_off(
    equity_bond_corr: Optional[float],
    equity_vol_corr: Optional[float],
    equity_gold_corr: Optional[float],
) -> bool:
    signals = 0
    if equity_bond_corr is not None and equity_bond_corr < -0.30:
        signals += 1
    if equity_vol_corr is not None and equity_vol_corr > -0.10:
        signals += 1
    if equity_gold_corr is not None and equity_gold_corr < -0.30:
        signals += 1
    return signals >= 2


def _triple_flight_to_safety(
    equity_bond_corr: Optional[float],
    equity_vol_corr: Optional[float],
    equity_gold_corr: Optional[float],
) -> bool:
    signals = 0
    if equity_bond_corr is not None and equity_bond_corr < -0.50:
        signals += 1
    if equity_vol_corr is not None and equity_vol_corr > 0.10:
        signals += 1
    if equity_gold_corr is not None and equity_gold_corr < -0.50:
        signals += 1
    return signals >= 2
