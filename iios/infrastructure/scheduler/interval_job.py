"""
iios/infrastructure/scheduler/interval_job.py
=============================================
Interval-based job scheduling helper.
"""

from __future__ import annotations

import datetime
from typing import Optional

__all__ = ["IntervalSchedule"]


class IntervalSchedule:
    """Tracks next-fire-time for a fixed-interval repeating job.

    Usage::

        schedule = IntervalSchedule(seconds=30)
        if schedule.is_due():
            run_job()
            schedule.mark_fired()
    """

    def __init__(
        self,
        seconds: float = 60.0,
        start: Optional[datetime.datetime] = None,
    ) -> None:
        self._interval = datetime.timedelta(seconds=seconds)
        self._next = (start or datetime.datetime.now()) + self._interval

    def is_due(self, now: Optional[datetime.datetime] = None) -> bool:
        return (now or datetime.datetime.now()) >= self._next

    def mark_fired(self, now: Optional[datetime.datetime] = None) -> None:
        """Update next-fire-time after the job ran."""
        fired_at = now or datetime.datetime.now()
        # Advance by one or more intervals to ensure next is in the future
        while self._next <= fired_at:
            self._next += self._interval

    @property
    def next_fire(self) -> datetime.datetime:
        return self._next

    @property
    def interval_seconds(self) -> float:
        return self._interval.total_seconds()
