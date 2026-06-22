"""
oios/db/universe.py

Universe registry CRUD operations for universe_stocks table.
This table is the single source of truth for the 230-symbol trading universe.

Writer:   seed_universe() at system init; manual maintenance only.
Readers:  Layer 0 fetchers, Layer 1A scanner, Layer 1.5 participation computation.
"""

from __future__ import annotations
import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class UniverseStock:
    symbol:              str
    company_name:        str
    sector:              str
    sector_purity_score: float = 1.0
    is_active:           bool  = True
    added_date:          str   = "2026-06-16"
    removed_date:        Optional[str] = None
    removal_reason:      Optional[str] = None


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_active_symbols(conn: sqlite3.Connection) -> list[str]:
    """Return list of all active symbols, ordered by sector then symbol."""
    rows = conn.execute(
        "SELECT symbol FROM universe_stocks WHERE is_active = 1 ORDER BY sector, symbol"
    ).fetchall()
    return [r[0] for r in rows]


def get_active_symbols_by_sector(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Return {sector: [symbols]} for all active stocks."""
    rows = conn.execute("""
        SELECT sector, symbol FROM universe_stocks
        WHERE is_active = 1
        ORDER BY sector, symbol
    """).fetchall()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row[0], []).append(row[1])
    return result


def get_stock(conn: sqlite3.Connection, symbol: str) -> Optional[UniverseStock]:
    row = conn.execute(
        "SELECT * FROM universe_stocks WHERE symbol = ?", (symbol,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    return UniverseStock(
        symbol              = d["symbol"],
        company_name        = d["company_name"],
        sector              = d["sector"],
        sector_purity_score = d["sector_purity_score"],
        is_active           = bool(d["is_active"]),
        added_date          = d["added_date"],
        removed_date        = d.get("removed_date"),
        removal_reason      = d.get("removal_reason"),
    )


def count_active(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM universe_stocks WHERE is_active = 1"
    ).fetchone()[0]


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def upsert_stock(conn: sqlite3.Connection, stock: UniverseStock) -> None:
    """Insert or replace a stock in the universe registry."""
    conn.execute("""
        INSERT OR REPLACE INTO universe_stocks
            (symbol, company_name, sector, sector_purity_score,
             is_active, added_date, removed_date, removal_reason)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        stock.symbol, stock.company_name, stock.sector, stock.sector_purity_score,
        1 if stock.is_active else 0, stock.added_date,
        stock.removed_date, stock.removal_reason,
    ))


def deactivate_stock(
    conn: sqlite3.Connection,
    symbol: str,
    removed_date: str,
    reason: str,
) -> None:
    """Mark a stock as removed (soft delete — history is preserved)."""
    conn.execute("""
        UPDATE universe_stocks
        SET is_active=0, removed_date=?, removal_reason=?
        WHERE symbol=?
    """, (removed_date, reason, symbol))


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

def seed_universe(conn: sqlite3.Connection, added_date: str = "2026-06-16") -> int:
    """
    Populate universe_stocks from the UNIVERSE_230 seed list.
    Uses INSERT OR IGNORE — safe to call multiple times. Returns count inserted.
    """
    from ..seeds.universe_230 import UNIVERSE_230

    cursor = conn.executemany("""
        INSERT OR IGNORE INTO universe_stocks
            (symbol, company_name, sector, sector_purity_score, is_active, added_date)
        VALUES (?,?,?,?,1,?)
    """, [
        (symbol, name, sector, purity, added_date)
        for symbol, name, sector, purity in UNIVERSE_230
    ])

    # Also sync to stock_sector_map for historical versioning
    conn.executemany("""
        INSERT OR IGNORE INTO stock_sector_map
            (symbol, primary_sector, sector_purity_score, effective_from)
        VALUES (?,?,?,?)
    """, [
        (symbol, sector, purity, added_date)
        for symbol, _, sector, purity in UNIVERSE_230
    ])

    n = cursor.rowcount
    log.info("[Universe] Seeded %d symbols into universe_stocks + stock_sector_map", n)
    return n
