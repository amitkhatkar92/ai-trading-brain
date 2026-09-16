"""
scripts/seed_broad_ohlcv_history_001.py
==========================================
One-time (re-runnable/incremental) OHLCV history seeder for the broader
Dhan NSE-EQ symbol universe (~2,438 symbols), so predictive_gap/
liquid_universe_builder_001.py can rank a genuinely broad liquidity pool
instead of just the ~209-230 symbols the existing daily OIOS refresh
currently maintains.

Deliberately standalone -- NOT wired into master_orchestrator.py or any
live cycle. Reuses oios/data/ohlcv_fetcher.py's already-tested,
already-in-production fetch/upsert logic directly (same function the
live daily refresh calls), just with a broader explicit symbol list
passed in -- never touches universe_stocks, never affects the existing
daily refresh's own symbol set or timing.

Run manually (e.g. via `docker exec -w /app <container> python3 -m
scripts.seed_broad_ohlcv_history_001`), ideally in the background --
network-bound, rate-limited by design (inter_symbol_delay_s), so it can
take a long time for a large symbol count. Safe to re-run: the
underlying fetcher is already incremental per-symbol (skips symbols
already up to date) and idempotent (INSERT OR IGNORE).
"""
from __future__ import annotations

import logging
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
)
log = logging.getLogger("seed_broad_ohlcv")

DB_PATH = ROOT / "data" / "market_behavior.db"
LOOKBACK_DAYS = 90
INTER_SYMBOL_DELAY_S = 0.3


def main() -> None:
    from predictive_gap.broad_market_universe import load_broad_nse_equity_symbols
    from oios.data.ohlcv_fetcher import run_daily_fetch

    bare_symbols = load_broad_nse_equity_symbols()
    if not bare_symbols:
        log.error("No broad symbol list available -- aborting.")
        return
    symbols = [f"{s}.NS" for s in bare_symbols]
    log.info("Seeding OHLCV history for %d broad-market symbols (lookback=%dd).",
              len(symbols), LOOKBACK_DAYS)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        t0 = time.monotonic()
        result = run_daily_fetch(
            conn, symbols, date.today().isoformat(),
            lookback_days=LOOKBACK_DAYS,
            inter_symbol_delay_s=INTER_SYMBOL_DELAY_S,
        )
        elapsed_min = (time.monotonic() - t0) / 60.0
        log.info(
            "DONE in %.1f min. ok=%d failed=%d rows_inserted=%d gaps=%d",
            elapsed_min, len(result.symbols_ok), len(result.symbols_failed),
            result.rows_inserted, len(result.gaps_by_symbol),
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
