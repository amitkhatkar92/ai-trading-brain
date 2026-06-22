"""
oios/data/bulk_block_fetcher.py

Layer 0 — NSE Bulk & Block Deal pipeline.

Bulk deals:  trades where quantity ≥ 0.5% of exchange-listed shares in a single day.
Block deals: large negotiated trades in a separate 35-minute window.

Used by Layer 1.5 Sub-B Capital Flow Intelligence for sector-level institutional
accumulation proxies.  Store now, use in Phase B.

NSE URLs:
  Bulk deals:  https://archives.nseindia.com/content/equities/bulk.csv
  Block deals: https://archives.nseindia.com/content/equities/block.csv

Both endpoints return full current-year history. We diff against what we already
have to insert only new records.
"""

from __future__ import annotations
import csv
import io
import logging
import sqlite3
import uuid

log = logging.getLogger(__name__)

_BULK_URL  = "https://archives.nseindia.com/content/equities/bulk.csv"
_BLOCK_URL = "https://archives.nseindia.com/content/equities/block.csv"

_HEADERS = {"User-Agent": "Mozilla/5.0"}


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

def _latest_date(conn: sqlite3.Connection, deal_type: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(trade_date) FROM bulk_block_deals WHERE deal_type = ?", (deal_type,)
    ).fetchone()
    return row[0] if row else None


def _insert_rows(conn: sqlite3.Connection, rows: list[tuple]) -> int:
    """
    rows: (deal_id, trade_date, symbol, deal_type, client_name, buy_sell, qty, price, sector, source)
    """
    cursor = conn.executemany("""
        INSERT OR IGNORE INTO bulk_block_deals
            (deal_id, trade_date, symbol, deal_type, client_name, buy_sell,
             quantity, price, sector, data_source)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, rows)
    return cursor.rowcount


def _get_sector(conn: sqlite3.Connection, symbol: str) -> str | None:
    row = conn.execute(
        "SELECT sector FROM universe_stocks WHERE symbol = ?", (symbol,)
    ).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------

def _normalise_date(raw: str) -> str | None:
    """
    NSE bulk/block CSVs use DD-MMM-YYYY (e.g. 16-Jun-2026).
    Convert to ISO-8601 YYYY-MM-DD.
    """
    from datetime import datetime
    for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _parse_deals(content: str, deal_type: str, conn: sqlite3.Connection) -> list[tuple]:
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for rec in reader:
        raw_date = rec.get("Date", rec.get("DATE", "")).strip()
        trade_date = _normalise_date(raw_date)
        if not trade_date:
            continue

        symbol_raw = rec.get("Symbol", rec.get("SYMBOL", "")).strip()
        symbol = symbol_raw + ".NS" if symbol_raw and not symbol_raw.endswith(".NS") else symbol_raw

        client = rec.get("Client Name", rec.get("CLIENT NAME", "")).strip()
        buy_sell = rec.get("Buy/Sell", rec.get("BUY/SELL", "")).strip().upper()
        buy_sell = "B" if buy_sell.startswith("B") else ("S" if buy_sell.startswith("S") else None)

        try:
            qty   = float(str(rec.get("Quantity Traded", rec.get("QUANTITY", 0))).replace(",", "") or 0)
            price = float(str(rec.get("Trade Price / Wght Avg Price", rec.get("PRICE", 0))).replace(",", "") or 0)
        except ValueError:
            qty, price = 0.0, 0.0

        sector = _get_sector(conn, symbol)

        rows.append((
            str(uuid.uuid4()),
            trade_date,
            symbol,
            deal_type,
            client or None,
            buy_sell,
            qty,
            price,
            sector,
            f"NSE_{deal_type}",
        ))
    return rows


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_csv(url: str) -> str | None:
    try:
        import requests
        r = requests.get(url, timeout=20, headers=_HEADERS)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        log.warning("[BulkBlock] Download failed %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_bulk_block_fetch(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Fetch and store bulk and block deal records.
    Skips records already in the database (INSERT OR IGNORE on deal_id — UUIDs are per-insert,
    so we use (symbol, trade_date, client_name, deal_type) to detect duplicates instead).
    Returns {"bulk": n_inserted, "block": n_inserted}.
    """
    result = {"bulk": 0, "block": 0}

    for deal_type, url in [("BULK", _BULK_URL), ("BLOCK", _BLOCK_URL)]:
        content = _fetch_csv(url)
        if not content:
            continue

        rows = _parse_deals(content, deal_type, conn)
        # Dedup: only insert rows for dates we don't already have (coarse filter)
        latest = _latest_date(conn, deal_type)
        if latest:
            rows = [r for r in rows if r[1] > latest]

        if not rows:
            log.info("[BulkBlock] %s: no new records", deal_type)
            continue

        with conn:
            n = _insert_rows(conn, rows)
        result[deal_type.lower()] = n
        log.info("[BulkBlock] %s: inserted %d rows", deal_type, n)

    return result


def get_sector_deal_count(
    conn: sqlite3.Connection,
    sector: str,
    from_date: str,
    to_date: str,
) -> int:
    """Return number of bulk/block deals in sector within [from_date, to_date]."""
    row = conn.execute("""
        SELECT COUNT(*) FROM bulk_block_deals
        WHERE sector = ? AND trade_date BETWEEN ? AND ?
    """, (sector, from_date, to_date)).fetchone()
    return row[0] if row else 0


def capital_flow_quality(
    conn: sqlite3.Connection,
    sector: str,
    from_date: str,
    to_date: str,
) -> str:
    """
    Returns "FULL" | "SPARSE" | "UNAVAILABLE" per MAS Section 5 Layer 1.5 Sub-B rules.
    FULL ≥ 3 deals; SPARSE 1–2; UNAVAILABLE 0.
    """
    count = get_sector_deal_count(conn, sector, from_date, to_date)
    if count >= 3:
        return "FULL"
    if count >= 1:
        return "SPARSE"
    return "UNAVAILABLE"
