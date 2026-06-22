"""
oios/db/calendar.py
Trading calendar utilities for OIOS.

All TTL and age computations use these functions exclusively.
Calendar day arithmetic is prohibited throughout OIOS (MAS_v1.2 Section 4, Table 1).

The trading_calendar table must be populated before any of these functions
are called. Use populate_trading_calendar() or the annual maintenance script.
"""

from __future__ import annotations
import sqlite3
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Core utilities
# ---------------------------------------------------------------------------

def count_trading_days(
    conn: sqlite3.Connection,
    from_date: str,
    to_date: str,
) -> int:
    """
    Count NSE trading days strictly after from_date and up to and including to_date.
    Both arguments are ISO-8601 date strings (YYYY-MM-DD).

    Example: from_date="2026-06-01", to_date="2026-06-05" with Mon-Fri trading
    and no holidays = 4 trading days (Tue, Wed, Thu, Fri; Mon is the from_date itself).
    """
    row = conn.execute("""
        SELECT COUNT(*) FROM trading_calendar
        WHERE calendar_date > ? AND calendar_date <= ?
          AND is_trading_day = 1
    """, (from_date, to_date)).fetchone()
    return row[0] if row else 0


def add_trading_days(
    conn: sqlite3.Connection,
    from_date: str,
    n_days: int,
) -> str:
    """
    Return the ISO-8601 date that is exactly n_days NSE trading days after from_date.
    from_date itself is not counted.

    Raises ValueError if the calendar does not contain enough future trading days.
    """
    if n_days == 0:
        return from_date
    row = conn.execute("""
        SELECT calendar_date FROM trading_calendar
        WHERE calendar_date > ? AND is_trading_day = 1
        ORDER BY calendar_date ASC
        LIMIT 1 OFFSET ?
    """, (from_date, n_days - 1)).fetchone()
    if not row:
        raise ValueError(
            f"[Calendar] Not enough trading days in calendar after {from_date} "
            f"(requested {n_days} days)"
        )
    return row[0]


def is_trading_day(conn: sqlite3.Connection, date_str: str) -> bool:
    """Return True if date_str is an NSE trading day."""
    row = conn.execute(
        "SELECT is_trading_day FROM trading_calendar WHERE calendar_date = ?",
        (date_str,),
    ).fetchone()
    if row is None:
        raise ValueError(f"[Calendar] Date {date_str} not found in trading_calendar")
    return bool(row[0])


# ---------------------------------------------------------------------------
# Calendar population utility (for tests and annual maintenance)
# ---------------------------------------------------------------------------

def populate_trading_calendar(
    conn: sqlite3.Connection,
    from_date: str,
    to_date: str,
    holidays: list[str] | None = None,
) -> int:
    """
    Populate trading_calendar for the date range [from_date, to_date] inclusive.
    Weekends (Sat/Sun) are always non-trading days.
    holidays is a list of additional ISO-8601 date strings to mark as non-trading.
    Returns the number of rows inserted.

    Safe to call multiple times — uses INSERT OR REPLACE.
    """
    holiday_set = set(holidays or [])
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)

    rows = []
    current = start
    while current <= end:
        date_str = current.isoformat()
        is_weekend = current.weekday() >= 5   # 5=Sat, 6=Sun
        is_holiday = date_str in holiday_set
        is_trading = 0 if (is_weekend or is_holiday) else 1
        holiday_name = None
        if is_weekend:
            holiday_name = "WEEKEND"
        elif is_holiday:
            holiday_name = holiday_set and "NSE_HOLIDAY" or None
        rows.append((date_str, is_trading, holiday_name))
        current += timedelta(days=1)

    conn.executemany(
        "INSERT OR REPLACE INTO trading_calendar (calendar_date, is_trading_day, holiday_name) "
        "VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


def populate_trading_calendar_with_names(
    conn: sqlite3.Connection,
    from_date: str,
    to_date: str,
    holidays: dict[str, str] | None = None,
) -> int:
    """
    Like populate_trading_calendar but holidays is a dict of {date_str: holiday_name}.
    """
    holiday_map = holidays or {}
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)

    rows = []
    current = start
    while current <= end:
        date_str = current.isoformat()
        is_weekend = current.weekday() >= 5
        is_holiday = date_str in holiday_map
        is_trading = 0 if (is_weekend or is_holiday) else 1
        if is_weekend:
            name = "WEEKEND"
        elif is_holiday:
            name = holiday_map[date_str]
        else:
            name = None
        rows.append((date_str, is_trading, name))
        current += timedelta(days=1)

    conn.executemany(
        "INSERT OR REPLACE INTO trading_calendar (calendar_date, is_trading_day, holiday_name) "
        "VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)
