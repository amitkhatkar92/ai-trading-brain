"""
oios/data/bhav_fetcher.py

Layer 0 — NSE BHAV Copy pipeline.

BHAV copies contain delivery percentage per symbol — the raw input for
the Layer 1B "Delivery Expansion" archetype (Phase B).

We store this data from Day 1 so history accumulates even before Layer 1B
is implemented. Missing one day of BHAV data cannot be back-filled from yfinance.

NSE BHAV URL pattern (CM segment):
  https://archives.nseindia.com/products/content/sec_bhavdata_full_{DDMONYYYY}.csv
  Example: sec_bhavdata_full_16JUN2026.csv

Fields used:
  SYMBOL, SERIES, DELIV_QTY, DELIV_PER, TRDQTY

On any network failure, the fetch is logged and skipped — no exception propagates.
"""

from __future__ import annotations
import io
import logging
import sqlite3
import uuid
from datetime import date

log = logging.getLogger(__name__)

# NSE BHAV URL template
_BHAV_URL = (
    "https://archives.nseindia.com/products/content/sec_bhavdata_full_{ddmonyyyy}.csv"
)

_MONTH_MAP = {
    1: "JAN", 2: "FEB",  3: "MAR",  4: "APR",
    5: "MAY", 6: "JUN",  7: "JUL",  8: "AUG",
    9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
}


def _bhav_url(trade_date: str) -> str:
    d = date.fromisoformat(trade_date)
    return _BHAV_URL.format(
        ddmonyyyy=f"{d.day:02d}{_MONTH_MAP[d.month]}{d.year}"
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

def upsert_bhav_rows(conn: sqlite3.Connection, rows: list[tuple]) -> int:
    """
    rows: (symbol, trade_date, series, traded_qty, deliverable_qty, delivery_pct, source)
    INSERT OR IGNORE — duplicate-date safe.
    """
    cursor = conn.executemany("""
        INSERT OR IGNORE INTO bhav_daily
            (symbol, trade_date, series, traded_quantity, deliverable_qty, delivery_pct, data_source)
        VALUES (?,?,?,?,?,?,?)
    """, rows)
    return cursor.rowcount


def has_bhav_for_date(conn: sqlite3.Connection, trade_date: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM bhav_daily WHERE trade_date = ? LIMIT 1", (trade_date,)
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Fetch + parse
# ---------------------------------------------------------------------------

def fetch_bhav(trade_date: str) -> list[tuple]:
    """
    Download and parse NSE BHAV copy for trade_date.
    Returns list of (symbol, trade_date, series, traded_qty, deliverable_qty, delivery_pct, source).
    Returns [] on any failure.
    """
    url = _bhav_url(trade_date)
    log.info("[BHAV] Fetching %s", url)

    try:
        import requests
        response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        content = response.text
    except Exception as exc:
        log.warning("[BHAV] Download failed for %s: %s", trade_date, exc)
        return []

    try:
        import csv
        reader = csv.DictReader(io.StringIO(content))
        rows = []
        for rec in reader:
            symbol = rec.get("SYMBOL", "").strip()
            series = rec.get("SERIES", "").strip()
            if not symbol or series not in ("EQ", "BE", "BL", "MF"):
                continue
            try:
                traded_qty    = float(rec.get("TRDQTY", 0) or 0)
                deliverable   = float(rec.get("DELIV_QTY", 0) or 0)
                delivery_pct_raw = rec.get("DELIV_PER", "").strip()
                delivery_pct  = float(delivery_pct_raw) / 100.0 if delivery_pct_raw else None
                rows.append((
                    symbol + ".NS",   # normalise to Yahoo Finance format
                    trade_date,
                    series,
                    traded_qty,
                    deliverable,
                    delivery_pct,
                    "NSE_BHAV",
                ))
            except (ValueError, TypeError) as exc:
                log.debug("[BHAV] Parse error on row %s: %s", rec, exc)
        log.info("[BHAV] Parsed %d rows for %s", len(rows), trade_date)
        return rows
    except Exception as exc:
        log.warning("[BHAV] Parse failed for %s: %s", trade_date, exc)
        return []


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_daily_bhav_fetch(
    conn: sqlite3.Connection,
    trade_date: str,
    force: bool = False,
) -> int:
    """
    Fetch and store BHAV for trade_date. Skip if already present (unless force=True).
    Returns count of rows inserted.
    """
    if not force and has_bhav_for_date(conn, trade_date):
        log.info("[BHAV] Already have data for %s — skipping", trade_date)
        return 0

    rows = fetch_bhav(trade_date)
    if not rows:
        return 0

    with conn:
        n = upsert_bhav_rows(conn, rows)
    log.info("[BHAV] Stored %d rows for %s", n, trade_date)
    return n
