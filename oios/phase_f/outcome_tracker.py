"""
oios/phase_f/outcome_tracker.py
Phase F Step F2.1 — Multi-Horizon Outcome Tracker

Updates market_leader_outcomes with forward returns at 1D, 3D, 5D, 10D, 20D horizons.
Classifies each leader's outcome type once the 20D horizon data is available.

Outcome Classes
---------------
ONE_DAY_SPIKE     : return_3d ≤ 0.5 × return_1d  (move reversed quickly)
SHORT_RUNNER      : return_5d > 0 but return_10d ≤ 0  (faded by week 2)
MULTI_WEEK_WINNER : return_10d > 3.0 and return_20d > 2.0
LONG_TREND_WINNER : return_20d > 5.0
UNKNOWN           : 20D window not yet available

Also updates control stock returns in market_research_controls.

ISOLATION CONTRACT
------------------
Reads:   ohlcv_daily, market_leaders_daily, market_research_controls
Writes:  market_leader_outcomes, market_research_controls (return columns)
No writes to any A–E table.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

# Outcome class thresholds (all in percentage points)
MULTI_WEEK_WIN_10D = 3.0
MULTI_WEEK_WIN_20D = 2.0
LONG_TREND_WIN_20D = 5.0

# Horizon definitions in trading days
HORIZONS = (1, 3, 5, 10, 20)


# ── Public API ────────────────────────────────────────────────────────────────

def update_outcomes(as_of_date: str, conn: sqlite3.Connection) -> int:
    """
    Update multi-horizon outcomes for all leaders where new price data is available.

    Called daily after OHLCV data is refreshed.

    Parameters
    ----------
    as_of_date : str
        ISO-8601 YYYY-MM-DD — the latest date for which OHLCV is available.
    conn : sqlite3.Connection
        OIOS DB connection.

    Returns
    -------
    int
        Number of outcome rows updated.
    """
    updated = 0
    leaders = _get_leaders_needing_update(as_of_date, conn)
    for leader in leaders:
        returns = _compute_forward_returns(
            leader["symbol"], leader["trade_date"], as_of_date, conn
        )
        if not returns:
            continue
        outcome_class = _classify(returns)
        mfe, mae = _compute_mfe_mae(
            leader["symbol"], leader["trade_date"], as_of_date, conn
        )
        _write_outcome(leader["leader_id"], returns, mfe, mae, outcome_class, conn)
        updated += 1

    # Also update controls
    updated += _update_control_outcomes(as_of_date, conn)

    log.info("[OutcomeTracker] %s: updated %d outcome rows", as_of_date, updated)
    return updated


# ── Leader outcome update ─────────────────────────────────────────────────────

def _get_leaders_needing_update(
    as_of_date: str, conn: sqlite3.Connection
) -> list[dict]:
    """
    Return leaders whose outcome rows are incomplete (any horizon still NULL
    that could now be populated given as_of_date).
    """
    rows = conn.execute("""
        SELECT mld.leader_id, mld.symbol, mld.trade_date,
               mlo.return_1d, mlo.return_3d, mlo.return_5d,
               mlo.return_10d, mlo.return_20d
        FROM market_leaders_daily mld
        LEFT JOIN market_leader_outcomes mlo ON mld.leader_id = mlo.leader_id
        WHERE mld.trade_date <= ?
          AND (mlo.return_20d IS NULL OR mlo.outcome_class = 'UNKNOWN')
    """, (as_of_date,)).fetchall()
    return [dict(r) for r in rows]


def _compute_forward_returns(
    symbol: str,
    trade_date: str,
    as_of_date: str,
    conn: sqlite3.Connection,
) -> dict[int, Optional[float]]:
    """
    Compute forward returns at each horizon.  Returns {days: pct_return or None}.
    """
    # Load enough history forward from trade_date
    rows = conn.execute("""
        SELECT trade_date, close
        FROM ohlcv_daily
        WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?
        ORDER BY trade_date ASC
        LIMIT 25
    """, (symbol, trade_date, as_of_date)).fetchall()

    if not rows or rows[0][0] != trade_date:
        return {}

    base_close = rows[0][1]
    if not base_close:
        return {}

    # Build {trading_day_offset → close}
    dates = [r[0] for r in rows]
    closes = [r[1] for r in rows]
    day_offset_map: dict[int, float] = {i: closes[i] for i in range(len(dates))}

    result: dict[int, Optional[float]] = {}
    for h in HORIZONS:
        if h < len(closes):
            result[h] = round((closes[h] - base_close) / base_close * 100, 4)
        else:
            result[h] = None
    return result


def _compute_mfe_mae(
    symbol: str,
    trade_date: str,
    as_of_date: str,
    conn: sqlite3.Connection,
) -> tuple[Optional[float], Optional[float]]:
    """Maximum Favorable / Maximum Adverse excursion within 20-trading-day window."""
    rows = conn.execute("""
        SELECT high, low, close
        FROM ohlcv_daily
        WHERE symbol = ? AND trade_date > ? AND trade_date <= ?
        ORDER BY trade_date ASC
        LIMIT 20
    """, (symbol, trade_date, as_of_date)).fetchall()

    base_row = conn.execute("""
        SELECT close FROM ohlcv_daily WHERE symbol = ? AND trade_date = ?
    """, (symbol, trade_date)).fetchone()

    if not base_row or not rows:
        return None, None

    base = base_row[0]
    if not base:
        return None, None

    highs  = [(r[0] - base) / base * 100 for r in rows if r[0]]
    lows   = [(r[1] - base) / base * 100 for r in rows if r[1]]

    mfe = round(max(highs), 4) if highs else None
    mae = round(min(lows), 4)  if lows  else None
    return mfe, mae


def _classify(returns: dict[int, Optional[float]]) -> str:
    r1  = returns.get(1)
    r3  = returns.get(3)
    r5  = returns.get(5)
    r10 = returns.get(10)
    r20 = returns.get(20)

    if r20 is None:
        return "UNKNOWN"
    if r20 > LONG_TREND_WIN_20D:
        return "LONG_TREND_WINNER"
    if r10 is not None and r10 > MULTI_WEEK_WIN_10D and r20 > MULTI_WEEK_WIN_20D:
        return "MULTI_WEEK_WINNER"
    # ONE_DAY_SPIKE must be checked before SHORT_RUNNER:
    # if the move reversed by day 3, it is a spike regardless of what r5/r10 show.
    if r1 is not None and r3 is not None and r3 <= 0.5 * r1:
        return "ONE_DAY_SPIKE"
    if r5 is not None and r5 > 0 and r10 is not None and r10 <= 0:
        return "SHORT_RUNNER"
    return "UNKNOWN"


def _write_outcome(
    leader_id: str,
    returns: dict[int, Optional[float]],
    mfe: Optional[float],
    mae: Optional[float],
    outcome_class: str,
    conn: sqlite3.Connection,
) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with conn:
        conn.execute("""
            INSERT INTO market_leader_outcomes
                (leader_id, return_1d, return_3d, return_5d, return_10d, return_20d,
                 max_favorable, max_adverse, outcome_class, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(leader_id) DO UPDATE SET
                return_1d      = excluded.return_1d,
                return_3d      = excluded.return_3d,
                return_5d      = excluded.return_5d,
                return_10d     = excluded.return_10d,
                return_20d     = excluded.return_20d,
                max_favorable  = excluded.max_favorable,
                max_adverse    = excluded.max_adverse,
                outcome_class  = excluded.outcome_class,
                updated_at     = excluded.updated_at
        """, (
            leader_id,
            returns.get(1), returns.get(3), returns.get(5),
            returns.get(10), returns.get(20),
            mfe, mae, outcome_class, now
        ))


# ── Control outcome update ────────────────────────────────────────────────────

def _update_control_outcomes(as_of_date: str, conn: sqlite3.Connection) -> int:
    """Update forward returns for control stocks that still have NULL horizons."""
    controls = conn.execute("""
        SELECT control_id, symbol, trade_date
        FROM market_research_controls
        WHERE return_20d IS NULL AND trade_date <= ?
    """, (as_of_date,)).fetchall()

    updated = 0
    now = datetime.utcnow().isoformat(timespec="seconds")
    for ctrl in controls:
        cid, sym, td = ctrl[0], ctrl[1], ctrl[2]
        returns = _compute_forward_returns(sym, td, as_of_date, conn)
        if not returns:
            continue
        outcome_class = _classify(returns)
        with conn:
            conn.execute("""
                UPDATE market_research_controls SET
                    return_1d     = ?,
                    return_3d     = ?,
                    return_5d     = ?,
                    return_10d    = ?,
                    return_20d    = ?,
                    outcome_class = ?
                WHERE control_id = ?
            """, (
                returns.get(1), returns.get(3), returns.get(5),
                returns.get(10), returns.get(20),
                outcome_class, cid
            ))
        updated += 1
    return updated
