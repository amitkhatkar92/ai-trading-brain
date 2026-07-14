"""iios/investment/portfolio/core/event_history.py

Thread-safe rolling event history store for the Institutional Portfolio Framework.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional

from iios.investment.portfolio.core.portfolio_events import (
    PortfolioEvent,
    PortfolioEventType,
)

_DEFAULT_MAX_SIZE = 2_000


@dataclass(frozen=True)
class EventRecord:
    """Persisted record of a dispatched portfolio event."""

    record_id:    str              = field(default_factory=lambda: str(uuid.uuid4()))
    event_id:     str              = ""
    event_type:   PortfolioEventType = PortfolioEventType.PORTFOLIO_UPDATED
    portfolio_id: str              = ""
    source:       str              = ""
    recorded_at:  float            = field(default_factory=time.time)
    handler_count:int              = 0
    failed_count: int              = 0
    duration_ms:  float            = 0.0
    event_dict:   dict             = field(default_factory=dict)

    @property
    def had_failures(self) -> bool:
        return self.failed_count > 0

    def to_dict(self) -> dict:
        return {
            "record_id":    self.record_id,
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "portfolio_id": self.portfolio_id,
            "source":       self.source,
            "recorded_at":  self.recorded_at,
            "handler_count":self.handler_count,
            "failed_count": self.failed_count,
            "duration_ms":  self.duration_ms,
        }


class EventHistory:
    """
    Thread-safe rolling deque of EventRecord objects.

    Supports filtering by portfolio_id, event_type, and time window.
    Oldest records are dropped when capacity is exceeded.
    """

    def __init__(self, max_size: int = _DEFAULT_MAX_SIZE) -> None:
        self._max  = max_size
        self._lock = threading.RLock()
        self._buf:  Deque[EventRecord] = deque(maxlen=max_size)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(
        self,
        event:         PortfolioEvent,
        *,
        handler_count: int   = 0,
        failed_count:  int   = 0,
        duration_ms:   float = 0.0,
    ) -> EventRecord:
        rec = EventRecord(
            event_id      = event.event_id,
            event_type    = event.event_type,
            portfolio_id  = event.portfolio_id,
            source        = event.source,
            handler_count = handler_count,
            failed_count  = failed_count,
            duration_ms   = duration_ms,
            event_dict    = event.to_dict(),
        )
        with self._lock:
            self._buf.append(rec)
        return rec

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def all(self) -> List[EventRecord]:
        with self._lock:
            return list(self._buf)

    def recent(self, n: int) -> List[EventRecord]:
        with self._lock:
            return list(self._buf)[-n:]

    def for_portfolio(self, portfolio_id: str) -> List[EventRecord]:
        with self._lock:
            return [r for r in self._buf if r.portfolio_id == portfolio_id]

    def by_type(self, event_type: PortfolioEventType) -> List[EventRecord]:
        with self._lock:
            return [r for r in self._buf if r.event_type == event_type]

    def since(self, timestamp: float) -> List[EventRecord]:
        with self._lock:
            return [r for r in self._buf if r.recorded_at >= timestamp]

    def count(self) -> int:
        with self._lock:
            return len(self._buf)

    def count_for_portfolio(self, portfolio_id: str) -> int:
        with self._lock:
            return sum(1 for r in self._buf if r.portfolio_id == portfolio_id)

    def failure_rate(self) -> float:
        """Fraction of dispatched events that had at least one handler failure."""
        with self._lock:
            if not self._buf:
                return 0.0
            failed = sum(1 for r in self._buf if r.had_failures)
            return failed / len(self._buf)

    def latest_for_portfolio(self, portfolio_id: str) -> Optional[EventRecord]:
        with self._lock:
            for rec in reversed(self._buf):
                if rec.portfolio_id == portfolio_id:
                    return rec
            return None

    def reset(self) -> None:
        with self._lock:
            self._buf.clear()
