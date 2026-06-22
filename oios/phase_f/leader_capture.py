"""
oios/phase_f/leader_capture.py
Phase F Step F1.1 — Daily Market Leader Capture

Captures the top-15 gainers (WINNER) and top-15 losers (LOSER)
from the active universe for a given trading date.

Source data: ohlcv_daily table (Phase A — already populated by existing data feeds).
Target:      market_leaders_daily + market_leader_outcomes (initial skeleton row).

ISOLATION CONTRACT
------------------
Reads:   ohlcv_daily, universe_stocks, sector_conviction_daily
Writes:  market_leaders_daily, market_leader_outcomes (skeleton)
No FK into A–E tables.  No EventBus emissions.  No OrderManager calls.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import uuid
from datetime import date, datetime
from typing import Optional

log = logging.getLogger(__name__)

# Number of leaders captured per side each day
LEADER_TOP_N = 15

# Minimum required OHLCV history (days) to compute volume_ratio
MIN_HISTORY_DAYS = 21


# ── Data object ───────────────────────────────────────────────────────────────

class LeaderRow:
    """Lightweight struct — avoids dataclass overhead for bulk inserts."""
    __slots__ = (
        "leader_id", "trade_date", "symbol", "leader_type", "rank_position",
        "day_return_pct", "volume_ratio", "sector", "theme_phase",
        "regime", "captured_at",
    )

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ── Core capture function ─────────────────────────────────────────────────────

def capture_daily_leaders(
    trade_date: str,
    conn: sqlite3.Connection,
    regime: Optional[str] = None,
) -> list[LeaderRow]:
    """
    Capture top-15 winners and top-15 losers for trade_date.

    Parameters
    ----------
    trade_date : str
        ISO-8601 YYYY-MM-DD.  Must be a trading day with OHLCV data.
    conn : sqlite3.Connection
        OIOS DB connection (WAL mode, FK enabled).
    regime : str, optional
        Market regime at capture time (e.g. 'bull_trend').
        If None, attempts to derive from global intelligence layer if available.

    Returns
    -------
    list[LeaderRow]
        Up to 30 rows (15 WINNER + 15 LOSER), or fewer if universe is small.
        Rows are persisted to market_leaders_daily before returning.
    """
    # 1. Load all universe symbols for this date
    symbols = _get_active_symbols(conn)
    if not symbols:
        log.warning("[LeaderCapture] No active universe symbols found — skipping %s", trade_date)
        return []

    # 2. Compute single-day returns for every symbol with data
    returns = _compute_returns(trade_date, symbols, conn)
    if len(returns) < 10:
        log.warning("[LeaderCapture] Only %d symbols have data for %s", len(returns), trade_date)

    # 3. Load sector and theme phase context
    sector_map   = _load_sector_map(conn)
    theme_map    = _load_theme_phases(trade_date, conn)
    vol_map      = _compute_volume_ratios(trade_date, symbols, conn)

    # 4. Sort and slice top-15 / bottom-15
    sorted_returns = sorted(returns.items(), key=lambda kv: kv[1], reverse=True)
    winners = sorted_returns[:LEADER_TOP_N]
    losers  = sorted_returns[-LEADER_TOP_N:]
    losers.reverse()   # rank_position 1 = deepest loser

    rows: list[LeaderRow] = []
    rows.extend(_build_rows(winners, "WINNER", trade_date, sector_map, theme_map, vol_map, regime))
    rows.extend(_build_rows(losers,  "LOSER",  trade_date, sector_map, theme_map, vol_map, regime))

    # 5. Persist (upsert — idempotent if re-run same day)
    _upsert_leaders(rows, conn)
    _init_outcome_rows(rows, conn)

    log.info("[LeaderCapture] %s: captured %d leaders (%d W + %d L)",
             trade_date, len(rows),
             sum(1 for r in rows if r.leader_type == "WINNER"),
             sum(1 for r in rows if r.leader_type == "LOSER"))
    return rows


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_active_symbols(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT symbol FROM universe_stocks WHERE is_active = 1"
    ).fetchall()
    return [r[0] for r in rows]


def _compute_returns(
    trade_date: str,
    symbols: list[str],
    conn: sqlite3.Connection,
) -> dict[str, float]:
    """
    For each symbol, compute (close_today - close_prev) / close_prev × 100.
    Only includes symbols with both today's and previous day's data.
    """
    placeholders = ",".join("?" * len(symbols))
    rows = conn.execute(f"""
        SELECT symbol, trade_date, close
        FROM ohlcv_daily
        WHERE symbol IN ({placeholders})
          AND trade_date <= ?
        ORDER BY symbol, trade_date DESC
    """, (*symbols, trade_date)).fetchall()

    # Group last two rows per symbol
    by_sym: dict[str, list[tuple[str, float]]] = {}
    for r in rows:
        sym, td, cl = r[0], r[1], r[2]
        by_sym.setdefault(sym, [])
        if len(by_sym[sym]) < 2:
            by_sym[sym].append((td, cl))

    returns: dict[str, float] = {}
    for sym, entries in by_sym.items():
        if len(entries) == 2:
            today_td, today_cl = entries[0]
            prev_td,  prev_cl  = entries[1]
            if today_td == trade_date and prev_cl and prev_cl != 0:
                returns[sym] = (today_cl - prev_cl) / prev_cl * 100.0
    return returns


def _load_sector_map(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT symbol, sector FROM universe_stocks").fetchall()
    return {r[0]: r[1] for r in rows}


def _load_theme_phases(trade_date: str, conn: sqlite3.Connection) -> dict[str, str]:
    """Return {sector: theme_phase} for the given date.  Empty dict if table missing data."""
    try:
        rows = conn.execute(
            "SELECT sector, theme_phase FROM sector_conviction_daily WHERE record_date = ?",
            (trade_date,)
        ).fetchall()
        return {r[0]: r[1] for r in rows if r[1]}
    except Exception:
        return {}


def _compute_volume_ratios(
    trade_date: str,
    symbols: list[str],
    conn: sqlite3.Connection,
) -> dict[str, float]:
    """volume_today / avg(volume, last 20 trading days before today)."""
    placeholders = ",".join("?" * len(symbols))
    rows = conn.execute(f"""
        SELECT symbol, trade_date, volume
        FROM ohlcv_daily
        WHERE symbol IN ({placeholders})
          AND trade_date <= ?
        ORDER BY symbol, trade_date DESC
    """, (*symbols, trade_date)).fetchall()

    by_sym: dict[str, list[tuple[str, float]]] = {}
    for r in rows:
        sym, td, vol = r[0], r[1], r[2]
        by_sym.setdefault(sym, [])
        if len(by_sym[sym]) < MIN_HISTORY_DAYS:
            by_sym[sym].append((td, vol))

    ratios: dict[str, float] = {}
    for sym, entries in by_sym.items():
        if not entries or entries[0][0] != trade_date:
            continue
        today_vol = entries[0][1]
        if len(entries) >= 2:
            prev_vols = [v for _, v in entries[1:] if v and v > 0]
            if prev_vols:
                avg_vol = sum(prev_vols) / len(prev_vols)
                ratios[sym] = today_vol / avg_vol if avg_vol else 1.0
    return ratios


def _make_leader_id(trade_date: str, symbol: str, leader_type: str, rank: int) -> str:
    """Deterministic ID so re-runs don't create duplicates."""
    raw = f"LDR|{trade_date}|{symbol}|{leader_type}|{rank}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"LDR_{trade_date.replace('-', '')}_{digest}"


def _build_rows(
    ranked: list[tuple[str, float]],
    leader_type: str,
    trade_date: str,
    sector_map: dict[str, str],
    theme_map: dict[str, str],
    vol_map: dict[str, float],
    regime: Optional[str],
) -> list[LeaderRow]:
    rows = []
    now = datetime.utcnow().isoformat(timespec="seconds")
    for rank, (sym, ret) in enumerate(ranked, start=1):
        sector = sector_map.get(sym, "UNKNOWN")
        rows.append(LeaderRow(
            leader_id      = _make_leader_id(trade_date, sym, leader_type, rank),
            trade_date     = trade_date,
            symbol         = sym,
            leader_type    = leader_type,
            rank_position  = rank,
            day_return_pct = round(ret, 4),
            volume_ratio   = round(vol_map.get(sym, 1.0), 3),
            sector         = sector,
            theme_phase    = theme_map.get(sector),
            regime         = regime,
            captured_at    = now,
        ))
    return rows


def _upsert_leaders(rows: list[LeaderRow], conn: sqlite3.Connection) -> None:
    sql = """
        INSERT OR REPLACE INTO market_leaders_daily
            (leader_id, trade_date, symbol, leader_type, rank_position,
             day_return_pct, volume_ratio, sector, theme_phase, regime, captured_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """
    with conn:
        conn.executemany(sql, [
            (r.leader_id, r.trade_date, r.symbol, r.leader_type, r.rank_position,
             r.day_return_pct, r.volume_ratio, r.sector, r.theme_phase,
             r.regime, r.captured_at)
            for r in rows
        ])


def _init_outcome_rows(rows: list[LeaderRow], conn: sqlite3.Connection) -> None:
    """Insert skeleton rows into market_leader_outcomes (all returns NULL initially)."""
    sql = """
        INSERT OR IGNORE INTO market_leader_outcomes
            (leader_id, outcome_class, updated_at)
        VALUES (?, 'UNKNOWN', ?)
    """
    now = datetime.utcnow().isoformat(timespec="seconds")
    with conn:
        conn.executemany(sql, [(r.leader_id, now) for r in rows])
