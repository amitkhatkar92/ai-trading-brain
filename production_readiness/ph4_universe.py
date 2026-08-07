"""
production_readiness/ph4_universe.py — Phase 4: Automatic Scanning Universe.

Builds and refreshes the eligible trading universe from nifty500_universe.json.
Applies liquidity filter (ADV >= MIN_ADV_CRORE) and data-quality checks.

No symbols are ever hardcoded. The universe file is the single source of truth.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .prr_config import (
    MIN_ADV_CRORE_AUTO,
    UNIVERSE_FILE,
    UNIVERSE_REFRESH_INTERVAL_H,
)
from .prr_models import UniverseCoverageReport, UniverseSymbol

log = logging.getLogger(__name__)


def load_raw_universe() -> List[dict]:
    """Load the raw universe JSON. Returns [] if file is missing/corrupt."""
    if not UNIVERSE_FILE.exists():
        log.warning("[Universe] nifty500_universe.json not found at %s", UNIVERSE_FILE)
        return []
    try:
        data = json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        log.warning("[Universe] Unexpected universe format (expected list).")
        return []
    except Exception as e:
        log.warning("[Universe] Cannot load universe: %s", e)
        return []


def _get_adv_from_data(symbol: str) -> float:
    """
    Try to get ADV (₹ crore) from the base/extended watchlist constants in the scanner.
    Falls back to 0.0 if not available (the symbol is still included — ADV checked separately).
    """
    try:
        from opportunity_engine.equity_scanner_ai import _BASE_WATCHLIST, _EXTENDED_WATCHLIST
        for entry in _BASE_WATCHLIST + _EXTENDED_WATCHLIST:
            if entry.get("symbol", "").strip() == symbol.strip():
                return float(entry.get("adv_crore", 0.0) or 0.0)
    except Exception:
        pass
    return 0.0


def get_eligible_symbols(
    raw: Optional[List[dict]] = None,
    min_adv_crore: float = MIN_ADV_CRORE_AUTO,
) -> Tuple[List[UniverseSymbol], List[UniverseSymbol]]:
    """
    Partition universe into (eligible, excluded).
    eligible: symbols that may be scanned
    excluded: symbols excluded with reason
    """
    if raw is None:
        raw = load_raw_universe()

    eligible: List[UniverseSymbol] = []
    excluded: List[UniverseSymbol] = []

    for entry in raw:
        if not isinstance(entry, dict):
            continue
        symbol = (entry.get("symbol") or "").strip()
        yahoo  = (entry.get("yahoo_ticker") or "").strip()
        sector = (entry.get("sector") or "UNKNOWN").strip()
        index  = (entry.get("index") or "").strip()
        adv    = float(entry.get("adv_crore", 0.0) or 0.0)

        if not symbol:
            continue

        # If ADV not in universe file, try to get from scanner's hardcoded tables
        if adv == 0.0:
            adv = _get_adv_from_data(symbol)

        if adv > 0 and adv < min_adv_crore:
            excluded.append(UniverseSymbol(
                symbol=symbol,
                yahoo_ticker=yahoo,
                sector=sector,
                index=index,
                adv_crore=adv,
                is_eligible=False,
                exclusion_reason=f"ADV={adv:.1f} Cr < threshold {min_adv_crore:.0f} Cr",
            ))
        elif not yahoo:
            excluded.append(UniverseSymbol(
                symbol=symbol,
                yahoo_ticker=yahoo,
                sector=sector,
                index=index,
                adv_crore=adv,
                is_eligible=False,
                exclusion_reason="Missing yahoo_ticker — cannot fetch market data",
            ))
        else:
            eligible.append(UniverseSymbol(
                symbol=symbol,
                yahoo_ticker=yahoo,
                sector=sector,
                index=index,
                adv_crore=adv,
                is_eligible=True,
            ))

    log.info(
        "[Universe] Eligible=%d Excluded=%d Total=%d (min_adv=%.0f Cr)",
        len(eligible), len(excluded), len(raw), min_adv_crore,
    )
    return eligible, excluded


def get_eligible_symbol_list(min_adv_crore: float = MIN_ADV_CRORE_AUTO) -> List[str]:
    """Return just the bare symbol strings for eligible universe members."""
    eligible, _ = get_eligible_symbols(min_adv_crore=min_adv_crore)
    return [s.symbol for s in eligible]


def build_dynamic_watchlist_rows(
    eligible: Optional[List[UniverseSymbol]] = None,
    price_map: Optional[Dict[str, float]] = None,
) -> List[dict]:
    """
    Build a watchlist row-list compatible with equity_scanner_ai._live_watchlist() output.
    Used as the dynamic fallback when the prepared universe is unavailable.
    """
    if eligible is None:
        eligible, _ = get_eligible_symbols()
    price_map = price_map or {}
    rows = []
    for sym in eligible:
        ltp = price_map.get(sym.symbol, 0.0)
        rows.append({
            "symbol":       sym.symbol,
            "ltp":          ltp,
            "resistance":   0.0,    # will be populated by scanner from live data
            "support":      0.0,
            "volume_ratio": 1.0,
            "rsi":          50.0,
            "adv_crore":    sym.adv_crore,
        })
    return rows


def build_universe_coverage_report(today: Optional[str] = None) -> UniverseCoverageReport:
    """Generate the UNIVERSE_COVERAGE_REPORT dataset."""
    today = today or datetime.now().date().isoformat()
    raw   = load_raw_universe()
    eligible, excluded = get_eligible_symbols(raw)

    total    = len(raw)
    n_elig   = len(eligible)
    n_excl   = len(excluded)
    cov_pct  = round(100 * n_elig / max(total, 1), 1)

    # Unexpected exclusions: symbols with zero ADV (data gap, not liquidity issue)
    unexpected = [e.symbol for e in excluded if e.adv_crore == 0.0 and e.exclusion_reason.startswith("ADV=0")]
    excl_breakdown: Dict[str, int] = {}
    for e in excluded:
        key = e.exclusion_reason.split(" ")[0]
        excl_breakdown[key] = excl_breakdown.get(key, 0) + 1

    log.info(
        "[Universe] Coverage report: total=%d eligible=%d excluded=%d "
        "cov=%.1f%% unexpected=%d",
        total, n_elig, n_excl, cov_pct, len(unexpected),
    )
    return UniverseCoverageReport(
        date=today,
        total_nifty500=total,
        eligible=n_elig,
        excluded=n_excl,
        coverage_pct=cov_pct,
        unexpected_exclusions=unexpected,
        exclusion_breakdown=excl_breakdown,
        symbols=eligible + excluded,
    )
