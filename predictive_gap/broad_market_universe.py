"""
predictive_gap/broad_market_universe.py
=========================================
DTA-MARKET-BENCHMARK-001 — broad (beyond-NIFTY500) NSE equity symbol list.

Reuses the existing Dhan security master (security_id_list.csv, already
shipped in the repo for order routing) instead of scraping nseindia.com
directly. Direct nseindia.com/archives access is confirmed BLOCKED (HTTP 503
via Akamai) from this environment — see OIOS_MARKET_DATA_PIPELINE_
REMEDIATION.md. yfinance (already used by predictive_gap/pga_collector.py
for the NIFTY500 benchmark) remains the price-fetch mechanism; this module
only supplies a broader SYMBOL LIST for that fetch.

Filter: SEM_EXM_EXCH_ID == "NSE" and SEM_SERIES == "EQ" — "EQ" is NSE's
standard series code for regular equity shares (T+1, normal trading).
This cleanly excludes SDLs/bonds/SG/MF/GS/BE/etc. series codes present in
the same file. ~2,460 symbols as of the current security_id_list.csv,
vs. 230 in nifty500_universe.json — genuinely broader, not a relabeled
NIFTY500 list.

Read-only. Never modifies security_id_list.csv or any trading state.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SECURITY_MASTER = _ROOT / "security_id_list.csv"

_cache: Optional[List[str]] = None
_cache_path: Optional[Path] = None


def load_broad_nse_equity_symbols(
    csv_path: Optional[Path] = None,
    force_reload: bool = False,
) -> List[str]:
    """Return the sorted, deduplicated list of bare NSE equity trading
    symbols (SEM_SERIES == 'EQ') from the Dhan security master file.

    Cached in-memory after first successful load (the file is ~65k rows;
    re-parsing per call would be wasteful for a value that only changes
    when the security master itself is refreshed). Pass force_reload=True
    to bypass the cache (used by tests).

    Returns [] on any read/parse failure — callers must treat an empty
    list as "broad-market collection unavailable this run", not "market
    is empty", and fail safe (never guess a stock in/out of the universe).
    """
    global _cache, _cache_path
    path = csv_path or DEFAULT_SECURITY_MASTER

    if not force_reload and _cache is not None and _cache_path == path:
        return list(_cache)

    symbols: set[str] = set()
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if (row.get("SEM_EXM_EXCH_ID") == "NSE"
                        and row.get("SEM_SERIES") == "EQ"):
                    sym = (row.get("SEM_TRADING_SYMBOL") or "").strip()
                    # Exclude NSE's own dummy/test securities (e.g. "011NSETEST")
                    # which carry SEM_SERIES='EQ' but are not real listings.
                    if sym and "NSETEST" not in sym:
                        symbols.add(sym)
    except Exception as exc:
        log.warning(
            "[BroadMarketUniverse] Failed to load %s: %s — "
            "broad-market benchmark unavailable this run.",
            path, exc,
        )
        return []

    result = sorted(symbols)
    _cache = result
    _cache_path = path
    log.info("[BroadMarketUniverse] Loaded %d NSE equity (SEM_SERIES=EQ) symbols from %s",
             len(result), path)
    return list(result)
