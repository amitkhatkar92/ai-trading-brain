"""
oios/engine/signal_outcome_tracker.py

Signal Outcome Tracker — Measurement Infrastructure Layer

ISOLATION CONTRACT
------------------
Reads:   signal_births (measurement cols only), ohlcv_daily
Writes:  signal_births: actual_move_pct, peak_move_pct, max_adverse_pct,
                        days_to_peak, final_state, final_age_trading_days,
                        last_updated_at

NEVER reads or writes:
  - opportunities table
  - decision_log
  - ct_decisions, ct_cycles (control_tower.db)
  - learning_db.json
  - StrategyHealthMonitor, MetaStrategyController
  - CapitalRiskEngine, OrderManager
  - Dhan API

This module is purely observational. It does not affect signal generation,
scoring, debate, execution, or position sizing in any way.

Signal outcome fields updated here are NOT read by:
  - re_calculator.compute_re()  (uses birth_price, base_score, expected_move_pct only)
  - decision_engine
  - strategy_lab

DIRECTION-AWARE DEFINITIONS
----------------------------
For LONG direction:
  actual_move_pct     = (close_at_obs - birth_price) / birth_price × 100
  peak_move_pct (MFE) = max((high - birth_price) / birth_price × 100) over window
  max_adverse_pct (MAE) = min((low - birth_price) / birth_price × 100) over window  [negative = adverse]

For SHORT direction:
  actual_move_pct     = (birth_price - close_at_obs) / birth_price × 100
  peak_move_pct (MFE) = max((birth_price - low) / birth_price × 100) over window
  max_adverse_pct (MAE) = min((birth_price - high) / birth_price × 100) over window [negative = adverse]

FINAL STATE TAXONOMY
--------------------
WIN     : peak_move_pct >= expected_move_pct × 0.5 (half-target reached at some point)
LOSS    : actual_move_pct < 0 and TTL exhausted
EXPIRED : TTL exhausted, actual_move_pct >= 0 but target never reached
PENDING : Signal within TTL — measurement captured but not yet final
NO_DATA : Required OHLCV data unavailable — cannot measure
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, NamedTuple

log = logging.getLogger(__name__)

# Win threshold fraction (half-target = win, consistent with outcome_distributor.py)
_WIN_THRESHOLD_FRACTION = 0.5

# Final state labels
FS_WIN     = "WIN"
FS_LOSS    = "LOSS"
FS_EXPIRED = "EXPIRED"
FS_PENDING = "PENDING"
FS_NO_DATA = "NO_DATA"


# ---------------------------------------------------------------------------
# Schema migration — add max_adverse_pct column if absent
# ---------------------------------------------------------------------------

def ensure_schema(conn: sqlite3.Connection) -> None:
    """Add max_adverse_pct column to signal_births if not present. Idempotent."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_births)").fetchall()}
    if "max_adverse_pct" not in cols:
        conn.execute(
            "ALTER TABLE signal_births ADD COLUMN max_adverse_pct REAL"
        )
        conn.commit()
        log.info("[SOT] Added max_adverse_pct column to signal_births.")


# ---------------------------------------------------------------------------
# OHLCV helpers
# ---------------------------------------------------------------------------

def _get_ohlcv_window(
    conn: sqlite3.Connection,
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """
    Return OHLCV rows for symbol in (start_date, end_date] (exclusive start).

    Returns list of dicts with keys: trade_date, open, high, low, close, volume.
    """
    rows = conn.execute("""
        SELECT trade_date, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE symbol = ?
          AND trade_date > ?
          AND trade_date <= ?
        ORDER BY trade_date ASC
    """, (symbol, start_date, end_date)).fetchall()

    return [
        {
            "trade_date": r[0], "open": r[1], "high": r[2],
            "low": r[3], "close": r[4], "volume": r[5],
        }
        for r in rows
    ]


def _observation_end_date(detected_at: str, expected_ttl_days: int, as_of_date: str) -> str:
    """
    Return the end date for the observation window:
    min(detected_at + expected_ttl_days calendar days, as_of_date).

    Uses calendar days (not trading days) as fallback since trading_calendar is empty.
    """
    try:
        det = date.fromisoformat(detected_at[:10])
        ttl_end = (det + timedelta(days=expected_ttl_days)).isoformat()
    except ValueError:
        return as_of_date
    return min(ttl_end, as_of_date)


def _calendar_days(detected_at: str, as_of_date: str) -> int:
    """Calendar days between detected_at and as_of_date."""
    try:
        d1 = date.fromisoformat(detected_at[:10])
        d2 = date.fromisoformat(as_of_date[:10])
        return (d2 - d1).days
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Single-signal outcome computation
# ---------------------------------------------------------------------------

class SignalOutcome(NamedTuple):
    signal_id:              str
    symbol:                 str
    direction:              str
    actual_move_pct:        float
    peak_move_pct:          Optional[float]   # MFE
    max_adverse_pct:        Optional[float]   # MAE (negative = adverse)
    days_to_peak:           Optional[int]
    final_state:            str
    final_age_calendar_days: int
    obs_end_date:           str


def compute_signal_outcome(
    conn: sqlite3.Connection,
    signal_id: str,
    symbol: str,
    direction: str,
    birth_price: float,
    detected_at: str,
    expected_ttl_days: int,
    expected_move_pct: float,
    as_of_date: str,
) -> Optional[SignalOutcome]:
    """
    Compute outcome for one signal. Returns None if OHLCV data is unavailable.

    Observation window: (detected_at, min(detected_at + ttl, as_of_date)]
    """
    if birth_price <= 0:
        return None

    obs_end = _observation_end_date(detected_at, expected_ttl_days, as_of_date)
    rows = _get_ohlcv_window(conn, symbol, detected_at, obs_end)

    if not rows:
        return SignalOutcome(
            signal_id=signal_id,
            symbol=symbol,
            direction=direction,
            actual_move_pct=0.0,
            peak_move_pct=None,
            max_adverse_pct=None,
            days_to_peak=None,
            final_state=FS_NO_DATA,
            final_age_calendar_days=0,
            obs_end_date=obs_end,
        )

    # Actual move at end of observation window (last close)
    last_close = rows[-1]["close"]
    if direction == "LONG":
        actual_move = (last_close - birth_price) / birth_price * 100.0
    else:
        actual_move = (birth_price - last_close) / birth_price * 100.0

    # MFE: maximum favorable excursion at any point in window
    peak_val: Optional[float] = None
    peak_idx: Optional[int] = None
    for i, r in enumerate(rows):
        if direction == "LONG":
            excursion = (r["high"] - birth_price) / birth_price * 100.0
        else:
            excursion = (birth_price - r["low"]) / birth_price * 100.0
        if peak_val is None or excursion > peak_val:
            peak_val = excursion
            peak_idx = i

    # MAE: maximum adverse excursion at any point in window
    mae_val: Optional[float] = None
    for r in rows:
        if direction == "LONG":
            excursion = (r["low"] - birth_price) / birth_price * 100.0  # negative = adverse
        else:
            excursion = (birth_price - r["high"]) / birth_price * 100.0  # negative = adverse
        if mae_val is None or excursion < mae_val:
            mae_val = excursion

    # Days to peak (calendar days from detected_at)
    days_to_peak: Optional[int] = None
    if peak_idx is not None:
        try:
            d_det = date.fromisoformat(detected_at[:10])
            d_peak = date.fromisoformat(rows[peak_idx]["trade_date"][:10])
            days_to_peak = (d_peak - d_det).days
        except ValueError:
            pass

    # Age in calendar days at observation end
    final_age = _calendar_days(detected_at, obs_end)

    # Is the signal still within its TTL?
    ttl_exhausted = obs_end < as_of_date or (
        _calendar_days(detected_at, as_of_date) > expected_ttl_days
    )

    # Final state classification
    win_threshold = expected_move_pct * _WIN_THRESHOLD_FRACTION
    if not ttl_exhausted:
        final_state = FS_PENDING
    elif peak_val is not None and peak_val >= win_threshold:
        final_state = FS_WIN
    elif actual_move < 0:
        final_state = FS_LOSS
    else:
        final_state = FS_EXPIRED

    return SignalOutcome(
        signal_id=signal_id,
        symbol=symbol,
        direction=direction,
        actual_move_pct=round(actual_move, 4),
        peak_move_pct=round(peak_val, 4) if peak_val is not None else None,
        max_adverse_pct=round(mae_val, 4) if mae_val is not None else None,
        days_to_peak=days_to_peak,
        final_state=final_state,
        final_age_calendar_days=final_age,
        obs_end_date=obs_end,
    )


# ---------------------------------------------------------------------------
# Batch resolver
# ---------------------------------------------------------------------------

def resolve_signal_outcomes(
    conn: sqlite3.Connection,
    as_of_date: str,
    dry_run: bool = False,
    signal_ids: Optional[list[str]] = None,
) -> dict:
    """
    Resolve outcomes for all (or specified) signal_births where final_state IS NULL.

    Parameters
    ----------
    conn : sqlite3.Connection
        Connection to market_behavior.db. Must have row_factory set.
    as_of_date : str
        Latest date for which OHLCV data is available. Typically MAX(trade_date)
        from ohlcv_daily.
    dry_run : bool
        If True, compute outcomes but do NOT write to the database.
    signal_ids : list[str] | None
        If provided, only process these signal_ids. Otherwise process all
        unresolved signals.

    Returns
    -------
    dict with summary metrics.
    """
    ensure_schema(conn)

    if signal_ids is not None:
        placeholders = ",".join("?" * len(signal_ids))
        query = f"""
            SELECT signal_id, symbol, expected_move_direction, birth_price,
                   detected_at, expected_ttl_days, expected_move_pct
            FROM signal_births
            WHERE final_state IS NULL
              AND signal_id IN ({placeholders})
        """
        rows = conn.execute(query, signal_ids).fetchall()
    else:
        rows = conn.execute("""
            SELECT signal_id, symbol, expected_move_direction, birth_price,
                   detected_at, expected_ttl_days, expected_move_pct
            FROM signal_births
            WHERE final_state IS NULL
        """).fetchall()

    total = len(rows)
    resolved    = 0
    pending     = 0
    no_data     = 0
    wins        = 0
    losses      = 0
    expired     = 0
    errors      = 0

    for row in rows:
        try:
            outcome = compute_signal_outcome(
                conn=conn,
                signal_id           = row[0],
                symbol              = row[1],
                direction           = row[2],
                birth_price         = row[3],
                detected_at         = row[4],
                expected_ttl_days   = row[5],
                expected_move_pct   = row[6] or 8.0,
                as_of_date          = as_of_date,
            )

            if outcome is None:
                errors += 1
                continue

            if outcome.final_state == FS_NO_DATA:
                no_data += 1
                continue

            if outcome.final_state == FS_PENDING:
                pending += 1
            elif outcome.final_state == FS_WIN:
                wins += 1
            elif outcome.final_state == FS_LOSS:
                losses += 1
            elif outcome.final_state == FS_EXPIRED:
                expired += 1

            if not dry_run:
                _write_outcome(conn, outcome)

            resolved += 1

        except Exception as exc:
            log.warning("[SOT] Error resolving %s %s: %s", row[0][:8], row[1], exc)
            errors += 1

    if not dry_run and resolved > 0:
        conn.commit()
        log.info(
            "[SOT] as_of=%s  resolved=%d  wins=%d  losses=%d  expired=%d  "
            "pending=%d  no_data=%d  errors=%d  total=%d",
            as_of_date, resolved, wins, losses, expired, pending, no_data, errors, total,
        )

    return {
        "as_of_date":   as_of_date,
        "dry_run":      dry_run,
        "total":        total,
        "resolved":     resolved,
        "wins":         wins,
        "losses":       losses,
        "expired":      expired,
        "pending":      pending,
        "no_data":      no_data,
        "errors":       errors,
        "win_rate":     wins / resolved if resolved > 0 else None,
    }


def _write_outcome(conn: sqlite3.Connection, outcome: SignalOutcome) -> None:
    """Persist measurement columns for one signal. Skips already-resolved signals."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn.execute("""
        UPDATE signal_births
        SET actual_move_pct        = ?,
            peak_move_pct          = ?,
            max_adverse_pct        = ?,
            days_to_peak           = ?,
            final_state            = ?,
            final_age_trading_days = ?,
            last_updated_at        = ?
        WHERE signal_id = ?
          AND final_state IS NULL
    """, (
        outcome.actual_move_pct,
        outcome.peak_move_pct,
        outcome.max_adverse_pct,
        outcome.days_to_peak,
        outcome.final_state,
        outcome.final_age_calendar_days,
        now,
        outcome.signal_id,
    ))


# ---------------------------------------------------------------------------
# Public convenience: run from orchestrator (observational, non-blocking)
# ---------------------------------------------------------------------------

def run_daily_outcome_resolution(
    conn: sqlite3.Connection,
    as_of_date: Optional[str] = None,
) -> dict:
    """
    Entry point for daily orchestrator call.

    Determines as_of_date from ohlcv_daily if not provided.
    Returns summary dict for logging.

    This function is OBSERVATIONAL ONLY. It does not affect:
    - Signal generation (scanner / signal_writer)
    - Decision engine (DecisionEngine / debate agents)
    - Strategy layer (MetaStrategyController / StrategyHealthMonitor)
    - Capital risk engine
    - Order manager
    - Dhan API
    """
    if as_of_date is None:
        row = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()
        as_of_date = row[0] if (row and row[0]) else date.today().isoformat()

    return resolve_signal_outcomes(conn, as_of_date)
