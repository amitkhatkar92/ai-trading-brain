"""
scripts/seed_sector_enrichment_001.py
=======================================
DTA-UNIVERSE-SECTOR-ENRICHMENT-001: one-time/re-runnable seeder script.

Populates data/sector_enrichment_cache.json with REAL sector data (via
yfinance) for every symbol currently in the active universe
(universe_stocks, is_active=1) that isn't already covered by either the
embedded-230 sector map or the enrichment cache. Deliberately NOT wired
into any live/scheduled path -- run manually via
`docker exec -w /app <container> python3 scripts/seed_sector_enrichment_001.py`.

Reuses predictive_gap/sector_enrichment_001.py's enrich_missing_sectors()
-- no new fetch/persistence logic here, this is pure orchestration.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "market_behavior.db"


def _load_active_universe_symbols() -> list:
    """Returns bare symbols (no .NS/.BO suffix) -- universe_stocks stores
    symbols WITH the .NS suffix (confirmed live), same normalization
    convention already used by liquid_universe_builder_001.py's
    _compute_adv_crore()."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            rows = conn.execute(
                "SELECT symbol FROM universe_stocks WHERE is_active=1"
            ).fetchall()
        finally:
            conn.close()
        return [r[0].replace(".NS", "").replace(".BO", "") for r in rows]
    except Exception as exc:
        log.error("Failed to load universe_stocks: %s", exc)
        return []


def main() -> None:
    from predictive_gap.sector_enrichment_001 import load_sector_cache, enrich_missing_sectors
    from opportunity_engine.market_scanner import _builtin_universe

    symbols = _load_active_universe_symbols()
    if not symbols:
        log.error("No active universe symbols found -- aborting.")
        return

    embedded = {e["symbol"] for e in _builtin_universe() if e.get("sector")}
    cache = load_sector_cache()
    already_covered = embedded | set(cache.keys())
    missing = [s for s in symbols if s not in already_covered]

    log.info(
        "Active universe=%d embedded-covered=%d cache-covered=%d still_missing=%d",
        len(symbols), len(embedded & set(symbols)), len(set(cache.keys()) & set(symbols)),
        len(missing),
    )
    if not missing:
        log.info("Nothing to do -- every active symbol already has a real sector.")
        return

    # Bounded per invocation; re-run to continue if the universe is large.
    result_cache = enrich_missing_sectors(missing, max_fetches=len(missing))
    found = len(set(result_cache.keys()) & set(missing))
    log.info("Done. Newly resolved this run: %d / %d missing.", found, len(missing))


if __name__ == "__main__":
    main()
