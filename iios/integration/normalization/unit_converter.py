"""iios/integration/normalization/unit_converter.py

Currency and numeric unit conversions.
"""
from __future__ import annotations

from typing import Any

from iios.integration.integration_exceptions import UnitConversionError

# Exchange rates (USD base). Populated at runtime via update_rates().
_DEFAULT_RATES: dict[str, float] = {
    "USD": 1.0,
    "INR": 83.5,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.0,
    "SGD": 1.35,
    "HKD": 7.82,
    "AUD": 1.53,
    "CAD": 1.36,
}


class UnitConverter:
    """
    Converts numeric values between units.

    Currently supports:
    - Currency pairs (via configurable exchange rates)
    - Price multipliers (paise→INR, cent→USD, etc.)
    - Quantity units (shares, lots)
    """

    def __init__(self, rates: dict[str, float] | None = None) -> None:
        self._rates: dict[str, float] = dict(_DEFAULT_RATES)
        if rates:
            self._rates.update(rates)

    def update_rates(self, rates: dict[str, float]) -> None:
        self._rates.update(rates)

    # ── Currency ──────────────────────────────────────────────────────────────

    def convert_currency(
        self,
        value:     float,
        from_ccy:  str,
        to_ccy:    str,
    ) -> float:
        """Convert *value* from *from_ccy* to *to_ccy* using USD as base."""
        if from_ccy == to_ccy:
            return value
        from_rate = self._rates.get(from_ccy.upper())
        to_rate   = self._rates.get(to_ccy.upper())
        if from_rate is None:
            raise UnitConversionError(f"Unknown currency: '{from_ccy}'")
        if to_rate is None:
            raise UnitConversionError(f"Unknown currency: '{to_ccy}'")
        # to USD then to target
        usd_value = value / from_rate
        return usd_value * to_rate

    def paise_to_inr(self, value: float) -> float:
        return value / 100.0

    def inr_to_paise(self, value: float) -> float:
        return value * 100.0

    def cents_to_usd(self, value: float) -> float:
        return value / 100.0

    # ── Quantity ──────────────────────────────────────────────────────────────

    def lots_to_shares(self, lots: float, lot_size: int) -> float:
        return lots * lot_size

    def shares_to_lots(self, shares: float, lot_size: int) -> float:
        if lot_size == 0:
            raise UnitConversionError("lot_size cannot be zero")
        return shares / lot_size

    # ── Percentage / BPS ─────────────────────────────────────────────────────

    def pct_to_bps(self, pct: float) -> float:
        return pct * 100.0

    def bps_to_pct(self, bps: float) -> float:
        return bps / 100.0

    def fraction_to_pct(self, fraction: float) -> float:
        return fraction * 100.0
