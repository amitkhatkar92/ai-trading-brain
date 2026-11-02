"""
tests/test_dta_itc_stale_band_001.py
========================================
DTA-ITC-STALE-BAND-001

Root cause (found via real 7-trading-day production review, 2026-11-02):
PRICE_INTEGRITY_SANITY_FAILURE fired repeatedly (8x) specifically for ITC
over other symbols. Confirmed live via yfinance: ITC Hotels demerger
(completed Jan 2026) permanently reduced ITC's real per-share price to
~Rs.260-266 as of 2026-11-02, while the registered sanity band was still
the pre-demerger (300, 600) -- so every single real post-demerger quote
was wrongly flagged as a sanity failure.
"""
from __future__ import annotations

from data_integrity.instrument_registry import get_instrument_registry


class TestITCStaleBandFix:
    def test_t01_real_current_itc_price_passes(self):
        """Real yfinance close observed 2026-10-27..2026-11-02: 259.5-265.6."""
        reg = get_instrument_registry()
        result = reg.check_price("ITC", 264.6)
        assert result.ok is True

    def test_t02_band_still_rejects_obviously_wrong_low_price(self):
        reg = get_instrument_registry()
        result = reg.check_price("ITC", 10.0)
        assert result.ok is False

    def test_t03_band_still_rejects_stale_pre_demerger_price(self):
        """A stale cached pre-demerger price (~460-500) should now also be
        caught, since it's no longer a realistic current ITC price."""
        reg = get_instrument_registry()
        result = reg.check_price("ITC", 480.0)
        assert result.ok is False

    def test_t04_band_tolerates_reasonable_volatility_range(self):
        reg = get_instrument_registry()
        for price in (200.0, 230.0, 260.0, 290.0, 320.0, 350.0):
            result = reg.check_price("ITC", price)
            assert result.ok is True, f"price={price} unexpectedly rejected"

    def test_t05_ns_suffix_normalized(self):
        reg = get_instrument_registry()
        result = reg.check_price("ITC.NS", 264.6)
        assert result.ok is True
