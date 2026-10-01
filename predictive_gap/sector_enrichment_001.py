"""
predictive_gap/sector_enrichment_001.py
========================================
DTA-UNIVERSE-SECTOR-ENRICHMENT-001: real-data sector enrichment for
symbols outside the original embedded 230-symbol universe.

liquid_universe_builder_001.py's _load_existing_sector_map() only ever
reused the hand-curated embedded-230 sector map, so every symbol added
by the Sep-2026 liquidity-ranked expansion (DTA-UNIVERSE-EXPANSION-001)
fell back to sector="UNKNOWN" -- confirmed live, 52%+ concentration in
UNKNOWN triggered weekend_intelligence.py's own Sunday concentration
review warning ("CONCENTRATED... governance review recommended").

Fetches REAL sector classifications via yfinance's .info (the same
library already used throughout this repo for OHLCV/price data -- no
new dependency, no fabricated/guessed labels). Persists results to a
small JSON cache (data/sector_enrichment_cache.json, gitignored) so a
previously-resolved symbol is never re-fetched -- yfinance .info calls
are comparatively slow (~0.5-2s each) and this cache is only ever read
by _load_existing_sector_map() during build_liquid_universe() (the
daily universe rebuild), never during a live trading cycle.

Fails safe throughout: a symbol that errors or returns no real sector
stays absent from the cache (never written as "UNKNOWN" -- that
fallback is applied downstream, not fabricated here) and is simply
retried on a future run. Read-only w.r.t. trading state; only ever
writes its own isolated cache file.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = _ROOT / "data" / "sector_enrichment_cache.json"

# yfinance .info calls are comparatively slow and rate-limit-sensitive;
# small delay between calls to stay a good citizen.
_FETCH_DELAY_SECONDS = 0.3

# Safety cap per run -- mirrors the max_items/bounded-backlog convention
# used elsewhere in this repo (e.g. DTA-EOD-BACKLOG-CAP-001). A symbol
# not reached this run is simply picked up on the next one.
_DEFAULT_MAX_FETCHES = 400


def load_sector_cache() -> Dict[str, str]:
    """Read-only accessor for the persisted real-sector cache. Returns
    {} if the cache doesn't exist yet or is unreadable -- never raises."""
    try:
        if not CACHE_PATH.exists():
            return {}
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, str) and v}
    except Exception as exc:
        log.warning("[SectorEnrichment] Failed to load cache: %s", exc)
        return {}


def _save_sector_cache(cache: Dict[str, str]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CACHE_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)
    tmp_path.replace(CACHE_PATH)


def fetch_real_sector(symbol: str) -> Optional[str]:
    """Fetch a single symbol's real sector via yfinance. Returns None on
    any failure or missing data -- never fabricates a value."""
    try:
        import yfinance as yf
        info = yf.Ticker(f"{symbol}.NS").info
        sector = info.get("sector")
        if isinstance(sector, str) and sector.strip():
            return sector.strip()
        return None
    except Exception as exc:
        log.debug("[SectorEnrichment] fetch failed for %s: %s", symbol, exc)
        return None


def enrich_missing_sectors(
    symbols: List[str],
    max_fetches: int = _DEFAULT_MAX_FETCHES,
) -> Dict[str, str]:
    """
    Fetches real sector data for any symbol in `symbols` not already in
    the persisted cache, bounded by `max_fetches` per call. Updates and
    returns the full merged cache (existing + newly fetched). Never
    raises -- a failure fetching one symbol never blocks the rest.
    """
    cache = load_sector_cache()
    missing = [s for s in symbols if s not in cache]
    fetched = 0
    newly_found = 0
    for symbol in missing:
        if fetched >= max_fetches:
            break
        fetched += 1
        sector = fetch_real_sector(symbol)
        if sector:
            cache[symbol] = sector
            newly_found += 1
        time.sleep(_FETCH_DELAY_SECONDS)
    if newly_found:
        try:
            _save_sector_cache(cache)
        except Exception as exc:
            log.warning("[SectorEnrichment] Failed to persist cache: %s", exc)
    log.info(
        "[SectorEnrichment] attempted=%d newly_found=%d still_missing=%d cache_size=%d",
        fetched, newly_found, max(0, len(missing) - fetched), len(cache),
    )
    return cache
