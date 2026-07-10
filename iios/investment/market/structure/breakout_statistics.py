"""iios/investment/market/structure/breakout_statistics.py
Track breakout statistics for quality assessment.
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List

from iios.investment.market.structure.models import (
    BreakoutEvent,
    BreakoutStatus,
    BreakoutType,
)

logger = logging.getLogger(__name__)


@dataclass
class BreakoutStats:
    total: int = 0
    confirmed: int = 0
    failed: int = 0
    retested: int = 0
    avg_follow_through: float = 0.0
    success_rate: float = 0.0


class BreakoutStatistics:
    """Rolling statistics over a window of breakout events."""

    def __init__(self, window: int = 50) -> None:
        self._window = window
        self._history: Deque[BreakoutEvent] = deque(maxlen=window)

    def record(self, event: BreakoutEvent) -> None:
        self._history.append(event)

    def get_stats(self) -> BreakoutStats:
        total = len(self._history)
        if total == 0:
            return BreakoutStats()
        confirmed = sum(
            1 for e in self._history if e.status == BreakoutStatus.CONFIRMED
        )
        failed = sum(
            1 for e in self._history if e.status == BreakoutStatus.FAILED
        )
        retested = sum(
            1 for e in self._history if e.status == BreakoutStatus.RETESTING
        )
        success = confirmed / total if total > 0 else 0.0
        avg_ft = self._avg_follow_through_all()
        return BreakoutStats(
            total=total,
            confirmed=confirmed,
            failed=failed,
            retested=retested,
            avg_follow_through=avg_ft,
            success_rate=success,
        )

    def success_rate(self) -> float:
        events = list(self._history)
        if not events:
            return 0.0
        confirmed = sum(1 for e in events if e.status == BreakoutStatus.CONFIRMED)
        return confirmed / len(events)

    def avg_follow_through(self, breakout_type: BreakoutType) -> float:
        events = [e for e in self._history if e.breakout_type == breakout_type]
        if not events:
            return 0.0
        return sum(e.close_beyond for e in events) / len(events)

    def _avg_follow_through_all(self) -> float:
        if not self._history:
            return 0.0
        return sum(e.close_beyond for e in self._history) / len(self._history)
