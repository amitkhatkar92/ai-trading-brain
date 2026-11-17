"""Previous-session close reference for judging whether a live price is plausible.

The live quote guards compare a price against a recent quote or a wide
instrument band. Neither exists at the next morning's open, so a bad open-time
quote can pass them. This module supplies an independent, volatility-scaled
reference: the last completed session's close and the symbol's own ATR%.

It is read-only and fails open (returns "plausible") whenever the reference is
missing, stale or unreadable, so it can only ever delay an action, never block
one for lack of data.
"""
from __future__ import annotations

import sqlite3
import statistics
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "market_behavior.db"
MIN_BAND = 0.07          # never flag a move smaller than 7%
ATR_MULTIPLE = 4.0       # a one-session move beyond 4 ATRs is treated as suspect
ATR_BARS = 14
MAX_REFERENCE_AGE_DAYS = 5

_cache: Dict[Tuple[str, str], Optional[Tuple[float, float]]] = {}
_lock = threading.Lock()


def _bare(symbol: str) -> str:
    return symbol.upper().replace(".NS", "").replace(".BO", "")


def _load_reference(symbol: str, today: str, db_path: Path) -> Optional[Tuple[float, float]]:
    """Return (previous_close, atr_fraction) or None when unavailable."""
    if not db_path.exists():
        return None
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT trade_date, high, low, close FROM ohlcv_daily "
            "WHERE symbol = ? AND trade_date < ? ORDER BY trade_date DESC LIMIT ?",
            (f"{_bare(symbol)}.NS", today, ATR_BARS + 1),
        ).fetchall()
    finally:
        conn.close()
    if len(rows) < ATR_BARS + 1:
        return None
    last_date, _, _, last_close = rows[0]
    if (date.fromisoformat(today) - date.fromisoformat(last_date)).days > MAX_REFERENCE_AGE_DAYS:
        return None
    if not last_close or last_close <= 0:
        return None
    true_ranges = []
    for index in range(ATR_BARS):
        _, high, low, _ = rows[index]
        previous_close = rows[index + 1][3]
        if None in (high, low, previous_close):
            return None
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return float(last_close), statistics.mean(true_ranges) / float(last_close)


def plausible_band(
    symbol: str, today: Optional[str] = None, db_path: Optional[Path] = None,
) -> Optional[Tuple[float, float, float]]:
    """Return (reference_close, lower, upper) for today's price, or None."""
    day = today or datetime.now().date().isoformat()
    key = (_bare(symbol), day)
    path = db_path or DB_PATH
    with _lock:
        if key not in _cache:
            try:
                _cache[key] = _load_reference(symbol, day, path)
            except (sqlite3.Error, ValueError, OSError) as exc:
                log.debug("[SessionCloseReference] %s unavailable: %s", symbol, exc)
                _cache[key] = None
        reference = _cache[key]
    if reference is None:
        return None
    close, atr_fraction = reference
    width = max(MIN_BAND, ATR_MULTIPLE * atr_fraction)
    return close, close * (1 - width), close * (1 + width)


def is_implausible_price(
    symbol: str, price: float, today: Optional[str] = None, db_path: Optional[Path] = None,
) -> bool:
    """True only when a reference exists and the price lies outside its band."""
    band = plausible_band(symbol, today, db_path)
    if band is None or price is None or price <= 0:
        return False
    return not band[1] <= price <= band[2]
