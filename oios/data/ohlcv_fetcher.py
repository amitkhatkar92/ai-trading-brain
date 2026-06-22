"""
oios/data/ohlcv_fetcher.py

Layer 0 — OHLCV data pipeline.

Fetches daily OHLCV for all active universe symbols via yfinance.
Writes to ohlcv_daily table via the repository, never directly.

Audit checks enforced:
  1. Duplicate date prevention     — INSERT OR IGNORE
  2. Missing date detection        — gap report after each fetch
  3. Split / corporate action flag — adjusted_close tracked separately
  4. Symbol rename / delist        — yfinance fetch failure logged, symbol not silently skipped

Data quality gate (MAS Section 5, Layer 0):
  Per-sector stocks_with_data / stocks_total computed after each fetch.
  If < 0.80, the sector is flagged PARTIAL for that date.
"""

from __future__ import annotations
import logging
import sqlite3
import time
from datetime import date, timedelta
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Repository layer (all DB writes go through here)
# ---------------------------------------------------------------------------

def get_latest_date(conn: sqlite3.Connection, symbol: str) -> Optional[str]:
    """Return the most recent trade_date in ohlcv_daily for symbol, or None."""
    row = conn.execute(
        "SELECT MAX(trade_date) FROM ohlcv_daily WHERE symbol = ?", (symbol,)
    ).fetchone()
    return row[0] if row and row[0] else None


def upsert_ohlcv_rows(
    conn: sqlite3.Connection,
    rows: list[tuple],
) -> int:
    """
    Insert OHLCV rows, ignoring duplicates.
    rows: list of (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
    Returns count of rows actually inserted (skips duplicates).
    """
    cursor = conn.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)
    return cursor.rowcount


def find_gaps(
    conn: sqlite3.Connection,
    symbol: str,
    from_date: str,
    to_date: str,
) -> list[str]:
    """
    Return trading dates in [from_date, to_date] that are missing from ohlcv_daily.
    Uses trading_calendar as reference — only NSE trading days are checked.
    """
    rows = conn.execute("""
        SELECT tc.calendar_date
        FROM trading_calendar tc
        LEFT JOIN ohlcv_daily od
            ON od.symbol = ? AND od.trade_date = tc.calendar_date
        WHERE tc.calendar_date BETWEEN ? AND ?
          AND tc.is_trading_day = 1
          AND od.trade_date IS NULL
        ORDER BY tc.calendar_date
    """, (symbol, from_date, to_date)).fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Fetch logic
# ---------------------------------------------------------------------------

def fetch_symbol_ohlcv(
    symbol: str,
    from_date: str,
    to_date: str,
    data_source: str = "YFINANCE",
) -> list[tuple]:
    """
    Fetch OHLCV from yfinance for one symbol.
    Returns list of (symbol, date_str, open, high, low, close, volume, adj_close, data_source).
    Returns [] on fetch failure (logged as warning).
    """
    try:
        import yfinance as yf
        df = yf.download(
            symbol,
            start=from_date,
            end=to_date,
            auto_adjust=False,
            progress=False,
            timeout=15,
        )
    except Exception as exc:
        log.warning("[OHLCV] yfinance fetch failed for %s: %s", symbol, exc)
        return []

    if df is None or df.empty:
        log.warning("[OHLCV] Empty data returned for %s (%s – %s)", symbol, from_date, to_date)
        return []

    # Flatten MultiIndex columns if present (yfinance ≥ 0.2.x multi-ticker format)
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    rows = []
    for idx, row in df.iterrows():
        trade_date = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
        try:
            rows.append((
                symbol,
                trade_date,
                round(float(row["Open"]),  4),
                round(float(row["High"]),  4),
                round(float(row["Low"]),   4),
                round(float(row["Close"]), 4),
                float(row["Volume"]),
                round(float(row["Adj Close"]), 4) if "Adj Close" in row else None,
                data_source,
            ))
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("[OHLCV] Row parse error for %s on %s: %s", symbol, trade_date, exc)
    return rows


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class OHLCVFetchResult:
    def __init__(self):
        self.symbols_ok:      list[str] = []
        self.symbols_failed:  list[str] = []
        self.rows_inserted:   int = 0
        self.gaps_by_symbol:  dict[str, list[str]] = {}


def run_daily_fetch(
    conn: sqlite3.Connection,
    symbols: list[str],
    today: str,
    lookback_days: int = 365,
    inter_symbol_delay_s: float = 0.5,
) -> OHLCVFetchResult:
    """
    Fetch OHLCV for all symbols and write to ohlcv_daily.
    For each symbol:
      - Determines the from_date as MAX(latest_in_db+1, today-lookback)
      - Fetches only incremental data
      - Checks for gaps after insert
      - Rate-limits with inter_symbol_delay_s

    Returns an OHLCVFetchResult summary.
    """
    result = OHLCVFetchResult()
    lookback_start = (date.fromisoformat(today) - timedelta(days=lookback_days)).isoformat()

    for symbol in symbols:
        latest = get_latest_date(conn, symbol)
        if latest is not None:
            # Incremental: start one day after the latest stored record
            from_date = (date.fromisoformat(latest) + timedelta(days=1)).isoformat()
        else:
            from_date = lookback_start

        if from_date > today:
            log.debug("[OHLCV] %s already up to date (latest=%s)", symbol, latest)
            result.symbols_ok.append(symbol)
            continue

        rows = fetch_symbol_ohlcv(symbol, from_date, today)
        if not rows:
            result.symbols_failed.append(symbol)
            log.warning("[OHLCV] No data fetched for %s from %s to %s", symbol, from_date, today)
            if inter_symbol_delay_s:
                time.sleep(inter_symbol_delay_s)
            continue

        with conn:
            n = upsert_ohlcv_rows(conn, rows)
        result.rows_inserted += n
        result.symbols_ok.append(symbol)
        log.info("[OHLCV] %s: inserted %d rows (fetched %d)", symbol, n, len(rows))

        # Gap detection — audit check
        gaps = find_gaps(conn, symbol, lookback_start, today)
        if gaps:
            result.gaps_by_symbol[symbol] = gaps
            log.warning("[OHLCV] Gap detected for %s: %d missing trading days", symbol, len(gaps))

        if inter_symbol_delay_s:
            time.sleep(inter_symbol_delay_s)

    log.info(
        "[OHLCV] Daily fetch complete. OK=%d  FAILED=%d  ROWS=%d  GAPS=%d",
        len(result.symbols_ok), len(result.symbols_failed),
        result.rows_inserted, len(result.gaps_by_symbol),
    )
    return result


def data_quality_report(
    conn: sqlite3.Connection,
    symbols_by_sector: dict[str, list[str]],
    trade_date: str,
) -> dict[str, dict]:
    """
    Compute per-sector data quality for a given trade_date.
    Returns {sector: {"total": n, "with_data": k, "quality": "FULL"|"PARTIAL"}}
    """
    report = {}
    for sector, symbols in symbols_by_sector.items():
        rows_with_data = conn.execute("""
            SELECT COUNT(DISTINCT symbol) FROM ohlcv_daily
            WHERE trade_date = ? AND symbol IN ({})
        """.format(",".join("?" * len(symbols))),
            [trade_date] + symbols
        ).fetchone()[0]
        total = len(symbols)
        quality = "FULL" if total == 0 or rows_with_data / total >= 0.80 else "PARTIAL"
        report[sector] = {"total": total, "with_data": rows_with_data, "quality": quality}
    return report
