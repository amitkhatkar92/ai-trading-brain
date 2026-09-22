"""
scripts/seed_multiyear_ohlcv_history_001.py
==============================================
DTA-UNIVERSE-COVERAGE-001

One-time (re-runnable) BACKWARD history extension for the active trading
universe (universe_stocks WHERE is_active=1, ~573 symbols).

Root cause this addresses: the existing daily OIOS incremental fetch
(oios/data/ohlcv_fetcher.py::run_daily_fetch) only ever extends FORWARD
from each symbol's existing MAX(trade_date) -- it can never backfill
OLDER history for a symbol that already has some (recent) data. The
September-2026 universe-expansion backfill (seed_broad_ohlcv_history_001.py)
only pulled a 90-day lookback, so every active-universe symbol's earliest
stored date is ~mid-2026 -- market_scanner.py's daily technical-level
computation (support/resistance) had no multi-year context to draw from.

This script fetches ONLY the missing OLDER window -- from
(today - LOOKBACK_DAYS) to (symbol's current earliest stored date - 1 day)
-- for every active-universe symbol, and inserts it via the same
idempotent upsert_ohlcv_rows() the live pipeline already uses (INSERT OR
IGNORE — safe to re-run). Never touches or duplicates the forward-
incremental range the daily refresh already maintains, and never touches
universe_stocks itself.

Deliberately standalone -- NOT wired into master_orchestrator.py or any
live cycle. Reuses oios/data/ohlcv_fetcher.py's already-tested fetch/
upsert primitives directly.

Run manually (network-bound, rate-limited by design):
    docker exec -w /app <container> python3 -m scripts.seed_multiyear_ohlcv_history_001
"""
from __future__ import annotations

import logging
import sqlite3
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
)
log = logging.getLogger("seed_multiyear_ohlcv")

DB_PATH = ROOT / "data" / "market_behavior.db"
LOOKBACK_DAYS = 730          # ~2 years
INTER_SYMBOL_DELAY_S = 0.3


def main() -> None:
    from oios.data.ohlcv_fetcher import fetch_symbol_ohlcv, upsert_ohlcv_rows

    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute(
            "SELECT symbol FROM universe_stocks WHERE is_active=1"
        ).fetchall()
        symbols = [r[0] for r in rows]
        if not symbols:
            log.error("No active universe symbols found -- aborting.")
            return
        log.info(
            "Extending history backward for %d active symbols (target lookback=%dd).",
            len(symbols), LOOKBACK_DAYS,
        )

        today = date.today()
        target_start = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()

        ok = failed = skipped = total_inserted = 0
        t0 = time.monotonic()
        for symbol in symbols:
            row = conn.execute(
                "SELECT MIN(trade_date) FROM ohlcv_daily WHERE symbol=?", (symbol,)
            ).fetchone()
            earliest = row[0] if row else None

            if earliest is None:
                # No data at all yet -- out of scope; the existing forward
                # daily refresh will pick this symbol up naturally.
                skipped += 1
                continue

            if earliest <= target_start:
                # Already has enough history -- nothing to backfill.
                skipped += 1
                continue

            backfill_end = (date.fromisoformat(earliest) - timedelta(days=1)).isoformat()
            fetch_rows = fetch_symbol_ohlcv(symbol, target_start, backfill_end)
            if not fetch_rows:
                failed += 1
                if INTER_SYMBOL_DELAY_S:
                    time.sleep(INTER_SYMBOL_DELAY_S)
                continue

            with conn:
                n = upsert_ohlcv_rows(conn, fetch_rows)
            total_inserted += n
            ok += 1
            log.info(
                "[MultiYearBackfill] %s: inserted %d older rows (%s -> %s)",
                symbol, n, target_start, backfill_end,
            )
            if INTER_SYMBOL_DELAY_S:
                time.sleep(INTER_SYMBOL_DELAY_S)

        elapsed_min = (time.monotonic() - t0) / 60.0
        log.info(
            "DONE in %.1f min. ok=%d failed=%d skipped=%d rows_inserted=%d",
            elapsed_min, ok, failed, skipped, total_inserted,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
