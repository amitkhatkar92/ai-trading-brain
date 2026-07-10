"""
Instrument Sanity Registry
==========================
Canonical metadata + expected price bands for every instrument the system
may trade. Used by the SL Integrity Gate and Price Integrity Validator to
detect obviously wrong prices BEFORE they can trigger stop-losses or entries.

Price bands reflect realistic NSE-traded ranges (not a guarantee — but any
quote that falls outside the band is treated as PRICE_INTEGRITY_FAILURE until
manually overridden or the band is updated).

Usage:
    from data_integrity.instrument_registry import get_instrument_registry
    reg = get_instrument_registry()
    result = reg.check_price("HINDALCO", 998.27)
    # result.ok      → False
    # result.reason  → "price 998.27 outside band [700, 1400] for HINDALCO"

Band maintenance:
    Bands should be updated periodically as market levels shift.
    Keep them wide enough to not false-positive normal volatility
    (e.g., ±50% around long-term range centre), but tight enough to
    catch clearly-wrong instruments (e.g., a ₹50 smallcap where ₹1000 is
    expected, or vice-versa).

Classification cutoff for legacy trades (security-ID fix deployment):
    SECURITY_ID_FIX_DEPLOYED = "2026-05-13T16:05:00"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from utils import get_logger

log = get_logger(__name__)

# ── Deployment timestamp of the security-ID fix ──────────────────────────────
# Trades opened BEFORE this timestamp were executed under unverified / possibly
# wrong instrument mappings (TATAMOTORS→TMPV, INFY→BHARTIARTL, etc.).
SECURITY_ID_FIX_DEPLOYED = datetime(2026, 5, 13, 16, 5, 0, tzinfo=timezone.utc)

# ── Price bands: (low, high) in ₹ ────────────────────────────────────────────
# Each entry represents the SANE range for NSE-traded prices.
# Outside this range → PRICE_INTEGRITY_FAILURE.
_BANDS: Dict[str, Tuple[float, float]] = {
    # ── Indices (spot/LTP values) ────────────────────────────────────────
    # NIFTY band covers both equity-spot (15k-30k) AND near-month futures/options
    # contract LTP which can be in the 800-1200 range per lot when quoted as
    # premium / contract-level price.  Use a wide band to avoid false positives.
    "NIFTY":         (  100.0,  30_000.0),
    "BANKNIFTY":     (  200.0,  60_000.0),
    "FINNIFTY":      (  100.0,  35_000.0),
    "MIDCAPNIFTY":   (   50.0,  20_000.0),
    "INDIAVIX":      (     5.0,      80.0),
    "SENSEX":        (  500.0, 100_000.0),

    # ── Large-Cap NSE Equities ────────────────────────────────────────────
    "HDFCBANK":      (1_200.0,  2_500.0),
    "RELIANCE":      (2_000.0,  3_500.0),
    "TCS":           (3_000.0,  5_000.0),
    "INFY":          (1_200.0,  2_500.0),
    "ICICIBANK":     (  900.0,  1_800.0),
    "KOTAKBANK":     (1_500.0,  2_800.0),
    "HINDUNILVR":    (2_200.0,  3_200.0),
    "ITC":           (  300.0,    600.0),
    "SBIN":          (  500.0,  1_100.0),
    "AXISBANK":      (  900.0,  1_600.0),
    "LT":            (3_000.0,  4_500.0),
    "WIPRO":         (  220.0,    600.0),
    "BAJFINANCE":    (6_000.0, 10_000.0),
    "MARUTI":        (10_000.0, 20_000.0),
    "BHARTIARTL":    ( 1_000.0,  2_500.0),
    "SUNPHARMA":     ( 1_400.0,  2_500.0),
    "TITAN":         ( 3_000.0,  5_000.0),
    "NESTLEIND":     (20_000.0, 30_000.0),
    "ULTRACEMCO":    ( 9_000.0, 14_000.0),
    "ASIANPAINT":    ( 2_000.0,  4_000.0),
    "TECHM":         ( 1_200.0,  2_500.0),
    "POWERGRID":     (   250.0,    450.0),
    "NTPC":          (   280.0,    500.0),
    "ONGC":          (   150.0,    400.0),
    "HCLTECH":       ( 1_500.0,  2_500.0),
    "ADANIENT":      ( 2_000.0,  4_000.0),
    "JSWSTEEL":      ( 1_000.0,  1_800.0),
    # TATAMOTORS: post-demerger TMCV (commercial vehicles). Range reflects
    # TMCV listing price zone (~₹600–₹900); adjust as price history builds.
    "TATAMOTORS":    (   400.0,  1_100.0),
    "TATASTEEL":     (   130.0,    300.0),
    "M&M":           ( 1_800.0,  3_500.0),
    "HINDALCO":      (   600.0,  1_500.0),
    "COALINDIA":     (   300.0,    650.0),

    # ── Pharma / Healthcare ───────────────────────────────────────────────────
    "LUPIN":         ( 1_800.0,  3_000.0),
    "DRREDDY":       ( 1_000.0,  1_800.0),
    "CIPLA":         ( 1_100.0,  1_900.0),
    "DIVISLAB":      ( 3_500.0,  6_500.0),
    "ALKEM":         ( 4_000.0,  7_500.0),
    "AUROPHARMA":    (   800.0,  1_700.0),
    "BIOCON":        (   200.0,    450.0),
    "TORNTPHARM":    ( 2_200.0,  4_200.0),
    "GLENMARK":      (   800.0,  1_800.0),
    "LAURUSLABS":    (   700.0,  1_600.0),
    "AJANTPHARM":    ( 1_800.0,  3_800.0),
    "PFIZER":        ( 4_000.0,  8_000.0),
    "GLAXO":         ( 1_600.0,  3_200.0),
    "SANOFI":        ( 4_500.0,  9_500.0),
    "ABBOTINDIA":    (18_000.0, 32_000.0),

    # ── FMCG / Consumer ──────────────────────────────────────────────────────
    "DABUR":         (   380.0,    620.0),
    "MARICO":        (   480.0,    760.0),
    "GODREJCP":      (   900.0,  1_700.0),
    "RADICO":        ( 1_400.0,  2_600.0),
    "BRITANNIA":     ( 5_000.0,  7_500.0),
    "TRENT":         ( 3_500.0,  9_000.0),
    "ABFRL":         (   170.0,    420.0),
    "KALYANKJIL":    (   250.0,    650.0),
    "PAGEIND":       (30_000.0, 55_000.0),
    "NYKAA":         (   100.0,    280.0),

    # ── Paints / Consumer Durables ────────────────────────────────────────────
    "PIDILITIND":    ( 2_200.0,  4_500.0),
    "BERGEPAINT":    (   420.0,    900.0),
    "AKZONOBEL":     ( 2_800.0,  5_000.0),
    "WHIRLPOOL":     ( 1_300.0,  2_600.0),
    "BLUESTARCO":    (   900.0,  2_200.0),
    "VOLTAS":        (   900.0,  2_000.0),

    # ── Financials (NBFCs, insurance) ─────────────────────────────────────────
    "LICHSGFIN":     (   420.0,    800.0),
    "MFSL":          ( 1_000.0,  2_000.0),
    "HDFCLIFE":      (   550.0,  1_000.0),
    "SBILIFE":       ( 1_200.0,  2_200.0),
    "ICICIGI":       ( 1_400.0,  2_500.0),
    "BAJAJFINSV":    ( 1_500.0,  2_500.0),

    # ── Infrastructure / Capital Goods ────────────────────────────────────────
    "RVNL":          (   280.0,    550.0),
    "MIDHANI":       (   280.0,    520.0),
    "PETRONET":      (   260.0,    440.0),
    "TORNTPOWER":    ( 1_600.0,  2_800.0),
    "NHPC":          (   100.0,    220.0),

    # ── Metals / Materials ────────────────────────────────────────────────────
    "NATIONALUM":    (   200.0,    440.0),
    "HINDZINC":      (   550.0,    900.0),
    "SHYAMMETL":     (   600.0,  1_100.0),
    "TATACHEM":      (   800.0,  1_400.0),

    # ── Misc mid/small cap ────────────────────────────────────────────────────
    "DMART":         ( 2_800.0,  5_800.0),
    "VBL":           (   420.0,    650.0),
    "NIFTYBEES":     (   220.0,    320.0),
    "BANKBEES":      (   440.0,    640.0),
}

# Instrument type labels (for threshold-aware logic downstream)
_ITYPE: Dict[str, str] = {
    "NIFTY": "INDEX", "BANKNIFTY": "INDEX", "FINNIFTY": "INDEX",
    "MIDCAPNIFTY": "INDEX", "INDIAVIX": "INDEX", "SENSEX": "INDEX",
}
# Default itype for anything not explicitly listed
_DEFAULT_ITYPE = "EQUITY"


@dataclass
class PriceCheckResult:
    ok:        bool
    symbol:    str
    price:     float
    band_low:  float
    band_high: float
    itype:     str
    reason:    str = ""


class InstrumentRegistry:
    """
    Canonical price-band and instrument-type store.
    Thread-safe for read access (bands never mutated at runtime).
    """

    def check_price(self, symbol: str, price: float) -> PriceCheckResult:
        """
        Returns PriceCheckResult.ok=True if price is within the sane band.
        Returns ok=False if symbol is unknown (no band registered) or price
        is outside the registered band.
        """
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        band = _BANDS.get(sym)
        itype = _ITYPE.get(sym, _DEFAULT_ITYPE)

        if band is None:
            # Unknown instrument — can't validate; treat as OK but log once
            log.debug("[InstrumentRegistry] No band for %s — skipping check", sym)
            return PriceCheckResult(
                ok=True, symbol=sym, price=price,
                band_low=0.0, band_high=float("inf"), itype=itype,
                reason="NO_BAND_REGISTERED",
            )

        low, high = band
        if low <= price <= high:
            return PriceCheckResult(
                ok=True, symbol=sym, price=price,
                band_low=low, band_high=high, itype=itype,
            )

        reason = (
            f"price {price:.2f} outside sanity band [{low:.0f}, {high:.0f}] "
            f"for {sym} (itype={itype})"
        )
        log.warning("[InstrumentRegistry] PRICE_INTEGRITY_FAILURE %s", reason)
        return PriceCheckResult(
            ok=False, symbol=sym, price=price,
            band_low=low, band_high=high, itype=itype,
            reason=reason,
        )

    def get_band(self, symbol: str) -> Optional[Tuple[float, float]]:
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        return _BANDS.get(sym)

    def get_itype(self, symbol: str) -> str:
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        return _ITYPE.get(sym, _DEFAULT_ITYPE)

    def is_known(self, symbol: str) -> bool:
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        return sym in _BANDS


# ── Singleton ─────────────────────────────────────────────────────────────────
_REGISTRY_INSTANCE: Optional["InstrumentRegistry"] = None


def get_instrument_registry() -> "InstrumentRegistry":
    global _REGISTRY_INSTANCE
    if _REGISTRY_INSTANCE is None:
        _REGISTRY_INSTANCE = InstrumentRegistry()
    return _REGISTRY_INSTANCE
