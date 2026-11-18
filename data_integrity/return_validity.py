"""Return-validity rules shared by every research consumer of price outcomes.

Raw prices in ``ohlcv_daily`` are unadjusted, and index symbols and market-holiday
placeholder bars share the same tables as stocks. A split, bonus or demerger therefore
looks like a 35-90% one-day "move", and an index stored in points looks like a +55,000%
return. Counting those as winners or losers corrupts every comparison of the
stock pools against real top performers.

This module only classifies; it never edits stored data and never touches trading
state. Callers decide what to exclude and should report the exclusion counts.
"""
from __future__ import annotations

import math
import sqlite3
from collections import Counter
from datetime import date, timedelta
from typing import Any, Iterable, Sequence

# NSE price bands are at most 20% for banded stocks, so a larger close-to-close step is
# virtually always a corporate action or a bad bar. The cap is deliberately above 20%
# because some unbanded names (new listings, F&O stocks) can legitimately move further.
MAX_PLAUSIBLE_STEP_PCT = 30.0
MAX_PLAUSIBLE_RETURN_PCT = {1: 30.0, 3: 40.0, 5: 50.0}

INDEX_SYMBOLS = frozenset({
    "NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX", "INDIAVIX",
})

REASON_INDEX = "INDEX_SYMBOL"
REASON_IMPLAUSIBLE = "IMPLAUSIBLE_RETURN_CORPORATE_ACTION_SUSPECT"
REASON_CORP_ACTION_WINDOW = "CORPORATE_ACTION_IN_FEATURE_WINDOW"


def is_index_symbol(symbol: Any) -> bool:
    text = str(symbol or "").upper().strip()
    return text.startswith("^") or text.removesuffix(".NS") in INDEX_SYMBOLS


def is_implausible_return(ret_pct: Any, horizon: int = 1) -> bool:
    """True for a non-finite return or one beyond what a real session can produce."""
    try:
        value = float(ret_pct)
    except (TypeError, ValueError):
        return True
    if not math.isfinite(value):
        return True
    cap = MAX_PLAUSIBLE_RETURN_PCT.get(horizon, MAX_PLAUSIBLE_STEP_PCT)
    return abs(value) > cap


def is_corporate_action_step(previous_close: Any, close: Any) -> bool:
    """True when consecutive real closes jump more than a market can move in a session."""
    try:
        prev, cur = float(previous_close), float(close)
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(prev) and math.isfinite(cur)) or prev <= 0 or cur <= 0:
        return False
    return abs(cur / prev - 1.0) * 100.0 > MAX_PLAUSIBLE_STEP_PCT


def find_corporate_actions(closes: Sequence[tuple[str, float, float | None]]) -> list[str]:
    """Dates (of the later bar) where a close-to-close step breaks the plausibility cap.

    ``closes`` is ordered oldest-first as (date, close, volume). Zero-volume rows are
    market-holiday placeholders that repeat the previous close, so they are skipped and
    never act as a reference or a break.
    """
    breaks: list[str] = []
    previous: float | None = None
    for day, close, volume in closes:
        if volume is not None and volume <= 0:
            continue
        if previous is not None and is_corporate_action_step(previous, close):
            breaks.append(day)
        previous = close
    return breaks


def symbols_with_corporate_action(
    conn: sqlite3.Connection, symbols: Iterable[str], start: str, end: str,
) -> dict[str, list[str]]:
    """Symbols whose stored closes between ``start`` and ``end`` contain a suspect step."""
    wanted = sorted({s for s in symbols if not is_index_symbol(s)})
    found: dict[str, list[str]] = {}
    for offset in range(0, len(wanted), 900):
        batch = wanted[offset:offset + 900]
        marks = ",".join("?" * len(batch))
        base = ("FROM ohlcv_daily WHERE symbol IN ({}) AND trade_date >= ? AND trade_date <= ? "
                "ORDER BY symbol, trade_date").format(marks)
        try:
            rows = conn.execute(f"SELECT symbol, trade_date, close, volume {base}",
                                (*batch, start, end)).fetchall()
        except sqlite3.OperationalError:
            rows = [(s, d, c, None) for s, d, c in conn.execute(
                f"SELECT symbol, trade_date, close {base}", (*batch, start, end))]
        series: dict[str, list[tuple[str, float, float | None]]] = {}
        for symbol, day, close, volume in rows:
            series.setdefault(symbol, []).append((day, close, volume))
        for symbol, data in series.items():
            hits = find_corporate_actions(data)
            if hits:
                found[symbol] = hits
    return found


def feature_window_start(trade_date: str, calendar_days: int = 60) -> str:
    """Start of the lookback the price features cover (about 40 sessions)."""
    return (date.fromisoformat(trade_date) - timedelta(days=calendar_days)).isoformat()


def validate_outcome_record(record: dict[str, Any]) -> str | None:
    """Reason a stored outcome row must not enter statistics, or ``None`` when usable."""
    if is_index_symbol(record.get("symbol")):
        return REASON_INDEX
    for horizon, key in ((1, "t1_ret_pct"), (3, "t3_ret_pct"), (5, "t5_ret_pct")):
        value = record.get(key)
        if value is not None and is_implausible_return(value, horizon):
            return REASON_IMPLAUSIBLE
    return None


def filter_valid_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter]:
    """Split rows into usable ones and a count of exclusions by reason."""
    usable: list[dict[str, Any]] = []
    excluded: Counter = Counter()
    for record in records:
        reason = validate_outcome_record(record)
        if reason:
            excluded[reason] += 1
        else:
            usable.append(record)
    return usable, excluded
