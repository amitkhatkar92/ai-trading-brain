"""
predictive_gap/liquid_universe_builder_001.py
================================================
Root-cause fix for the live trading universe cap: data/nifty500_universe.json
was a STATIC, embedded 230-symbol list because NSE direct access is
blocked (Akamai) -- see broad_market_universe.py's own docstring, and
orchestrator/master_orchestrator.py::_run_weekly_universe_rebuild()'s
explicit comment ("NSE direct is unreachable from the VPS ... the
embedded 230-symbol list is used"). This builds a genuinely broader,
liquidity-filtered universe using Dhan's already-accessible security
master (~2,460 real NSE EQ symbols, via broad_market_universe.py) plus
real average-daily-traded-value (ADV) computed from ohlcv_daily,
selecting the top TARGET_UNIVERSE_SIZE most liquid names.

Output schema matches the existing nifty500_universe.json format exactly
(symbol, yahoo_ticker, sector, index, adv_crore) so every existing
consumer (20+ files across opportunity_engine/, production_readiness/,
predictive_gap/, autonomous_research/, hkap/) works unchanged. Sector is
reused from the existing embedded 230-symbol list where available;
unmapped new symbols get sector="UNKNOWN" -- already a handled fallback
everywhere this field is read (e.g. equity_scanner_ai.py's own
`stock.get("sector") or _SYMBOL_SECTOR_MAP.get(_sym, "UNKNOWN")`).

Fails safe: returns None (never a partial/empty list) on any error, so
callers must fall back to the existing embedded-230 universe.

Read-only w.r.t. trading state. Only reads ohlcv_daily (SELECT only) and
the Dhan security master CSV (via broad_market_universe.py, also
read-only). Never writes to any database table.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "market_behavior.db"

# User-confirmed target (2026-09-16): ~500 symbols, ADV-filtered.
TARGET_UNIVERSE_SIZE = 500
ADV_LOOKBACK_DAYS = 20

# Sanity floor: if far fewer liquid symbols are found than requested,
# something upstream is wrong (e.g. ohlcv_daily mostly stale/empty) --
# fail safe rather than silently ship a much-smaller-than-intended universe.
_MIN_ACCEPTABLE_FRACTION = 0.5

# DTA-UNIVERSE-FRESHNESS-001: a symbol's ADV must be computed from data no
# older than this many calendar days behind the table's own latest known
# trade_date, or it is excluded from ranking entirely. Prevents a stale
# (e.g. weeks-old) ADV snapshot from a since-excluded symbol silently
# outranking a genuinely fresh, currently-tracked candidate. 10 days gives
# a safety margin over normal weekend/holiday gaps (max ~4 calendar days).
MAX_ADV_STALENESS_DAYS = 10


def _load_existing_sector_map() -> Dict[str, str]:
    """Reuse sector labels already curated in the embedded 230-symbol
    list, merged with any real sectors persisted by the sector-enrichment
    cache (DTA-UNIVERSE-SECTOR-ENRICHMENT-001, predictive_gap.
    sector_enrichment_001) for symbols outside that original list --
    never invents new sector classifications. Embedded-230 labels take
    precedence on overlap (same convention as before this change)."""
    merged: Dict[str, str] = {}
    try:
        from predictive_gap.sector_enrichment_001 import load_sector_cache
        merged.update(load_sector_cache())
    except Exception as exc:
        log.warning("[LiquidUniverse] Could not load sector enrichment cache: %s", exc)
    try:
        from opportunity_engine.market_scanner import _builtin_universe
        merged.update({e["symbol"]: e["sector"] for e in _builtin_universe() if e.get("sector")})
    except Exception as exc:
        log.warning("[LiquidUniverse] Could not load existing sector map: %s", exc)
    return merged


def _compute_adv_crore(db_path: Path) -> Dict[str, float]:
    """Real average daily traded value (close * volume, in Rs crore) over
    the last ADV_LOOKBACK_DAYS trading days per symbol, from ohlcv_daily.
    Keys are normalised to bare symbols (no .NS/.BO suffix) to match
    broad_market_universe.load_broad_nse_equity_symbols()'s convention --
    ohlcv_daily itself stores symbols WITH the .NS suffix (e.g.
    "ADANIPORTS.NS"), confirmed via live production data. Returns {} on
    any failure -- callers must treat this as "no ADV data available this
    run", not "zero-liquidity market".

    DTA-UNIVERSE-FRESHNESS-001: a symbol whose most recent row is more than
    MAX_ADV_STALENESS_DAYS behind the table's own latest trade_date is
    excluded -- its ADV value cannot be trusted to reflect current
    liquidity (verified live: ~20% of the universe was being selected off
    ADV snapshots ~7 weeks stale before this fix)."""
    result: Dict[str, float] = {}
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            latest_row = conn.execute(
                "SELECT MAX(trade_date) FROM ohlcv_daily WHERE symbol NOT LIKE '^%'"
            ).fetchone()
            latest_date = latest_row[0] if latest_row else None

            rows = conn.execute(
                """
                SELECT symbol, AVG(close * volume) / 1e7 AS adv_crore, MAX(trade_date) AS last_dt
                FROM (
                    SELECT symbol, close, volume, trade_date,
                           ROW_NUMBER() OVER (
                               PARTITION BY symbol ORDER BY trade_date DESC
                           ) AS rn
                    FROM ohlcv_daily
                    WHERE symbol NOT LIKE '^%'
                )
                WHERE rn <= ?
                GROUP BY symbol
                """,
                (ADV_LOOKBACK_DAYS,),
            ).fetchall()
        finally:
            conn.close()

        stale_excluded = 0
        for symbol, adv, last_dt in rows:
            if adv is None:
                continue
            if latest_date and last_dt and _days_between(last_dt, latest_date) > MAX_ADV_STALENESS_DAYS:
                stale_excluded += 1
                continue
            bare_symbol = symbol.replace(".NS", "").replace(".BO", "")
            result[bare_symbol] = round(float(adv), 2)
        if stale_excluded:
            log.info("[LiquidUniverse] Excluded %d symbol(s) with ADV data >%d days stale "
                      "(latest table date=%s).", stale_excluded, MAX_ADV_STALENESS_DAYS, latest_date)
    except Exception as exc:
        log.warning("[LiquidUniverse] ADV computation failed: %s", exc)
    return result


def _days_between(earlier: str, later: str) -> int:
    """Calendar days between two ISO date strings. Returns a large number
    (always "stale") on any parse failure, never raises."""
    try:
        from datetime import date as _date
        d1 = _date.fromisoformat(str(earlier)[:10])
        d2 = _date.fromisoformat(str(later)[:10])
        return (d2 - d1).days
    except Exception:
        return 10_000


def build_liquid_universe(
    target_size: int = TARGET_UNIVERSE_SIZE,
    db_path: Optional[Path] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Build a liquidity-ranked universe of up to `target_size` symbols from
    Dhan's broad NSE-EQ security master, filtered/ranked by real ADV.

    Returns None (never a partial list) on any failure -- caller must fall
    back to the existing embedded universe. Never raises.
    """
    try:
        from predictive_gap.broad_market_universe import load_broad_nse_equity_symbols
        broad_symbols = load_broad_nse_equity_symbols()
        if not broad_symbols:
            log.warning("[LiquidUniverse] Broad symbol list unavailable -- aborting.")
            return None

        adv_map = _compute_adv_crore(db_path or DEFAULT_DB_PATH)
        if not adv_map:
            log.warning("[LiquidUniverse] No ADV data available -- aborting.")
            return None

        sector_map = _load_existing_sector_map()

        ranked = sorted(
            ((s, adv_map[s]) for s in broad_symbols if s in adv_map and adv_map[s] > 0),
            key=lambda item: -item[1],
        )
        top = ranked[:target_size]

        if len(top) < target_size * _MIN_ACCEPTABLE_FRACTION:
            log.warning(
                "[LiquidUniverse] Only %d/%d liquid symbols found -- aborting "
                "(below %.0f%% sanity floor).",
                len(top), target_size, _MIN_ACCEPTABLE_FRACTION * 100,
            )
            return None

        universe: List[Dict[str, Any]] = []
        for symbol, adv in top:
            existing_sector = sector_map.get(symbol)
            universe.append({
                "symbol": symbol,
                "yahoo_ticker": f"{symbol}.NS",
                "sector": existing_sector or "UNKNOWN",
                "index": "NIFTY500" if existing_sector else "BROADMARKET_LIQUID",
                "adv_crore": adv,
            })
        log.info(
            "[LiquidUniverse] Built %d-symbol liquidity-filtered universe "
            "(target=%d, min_adv=%.2f Cr, max_adv=%.2f Cr).",
            len(universe), target_size,
            universe[-1]["adv_crore"] if universe else 0.0,
            universe[0]["adv_crore"] if universe else 0.0,
        )
        return universe
    except Exception as exc:
        log.warning("[LiquidUniverse] build_liquid_universe failed: %s", exc)
        return None
