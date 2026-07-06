"""
iios/infrastructure/scheduler/cron_job.py
==========================================
Cron-style job scheduling with simple expression parser.

Supports: ``* */5 9-17 * 1-5`` (minute, hour, dom, month, dow).
"""

from __future__ import annotations

import datetime
from typing import Optional

__all__ = ["CronExpression"]


def _parse_field(field: str, lo: int, hi: int) -> set[int]:
    """Parse a single cron field into a set of integers."""
    if field == "*":
        return set(range(lo, hi + 1))

    values: set[int] = set()
    for part in field.split(","):
        if "/" in part:
            range_part, step_str = part.split("/", 1)
            step = int(step_str)
            if range_part == "*":
                values.update(range(lo, hi + 1, step))
            elif "-" in range_part:
                a, b = range_part.split("-", 1)
                values.update(range(int(a), int(b) + 1, step))
            else:
                values.update(range(int(range_part), hi + 1, step))
        elif "-" in part:
            a, b = part.split("-", 1)
            values.update(range(int(a), int(b) + 1))
        else:
            values.add(int(part))

    return values


class CronExpression:
    """Parses and evaluates a 5-field cron expression.

    Format: ``<minute> <hour> <day-of-month> <month> <day-of-week>``

    Examples::

        CronExpression("*/5 * * * *")      # every 5 minutes
        CronExpression("0 9 * * 1-5")      # 09:00 Mon–Fri
        CronExpression("30 17 * * *")      # 17:30 every day
    """

    def __init__(self, expression: str) -> None:
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(
                f"Cron expression must have exactly 5 fields, got {len(parts)}: {expression!r}"
            )
        self._raw = expression
        self._minutes = _parse_field(parts[0], 0, 59)
        self._hours = _parse_field(parts[1], 0, 23)
        self._days = _parse_field(parts[2], 1, 31)
        self._months = _parse_field(parts[3], 1, 12)
        self._weekdays = _parse_field(parts[4], 0, 6)  # 0=Sunday

    def matches(self, dt: Optional[datetime.datetime] = None) -> bool:
        """Return True if *dt* (defaults to now) matches the expression."""
        if dt is None:
            dt = datetime.datetime.now()
        return (
            dt.minute in self._minutes
            and dt.hour in self._hours
            and dt.day in self._days
            and dt.month in self._months
            and dt.weekday() in {(d - 1) % 7 for d in self._weekdays}
        )

    def next_fire(self, after: Optional[datetime.datetime] = None) -> datetime.datetime:
        """Return the next datetime this expression fires after *after* (exclusive)."""
        now = (after or datetime.datetime.now()).replace(second=0, microsecond=0)
        candidate = now + datetime.timedelta(minutes=1)
        # Search up to 1 year
        for _ in range(366 * 24 * 60):
            if self.matches(candidate):
                return candidate
            candidate += datetime.timedelta(minutes=1)
        raise RuntimeError(f"No next fire time found for expression {self._raw!r}")

    def __str__(self) -> str:
        return self._raw

    def __repr__(self) -> str:
        return f"CronExpression({self._raw!r})"
