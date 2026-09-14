"""engine/event_scheduler.py — Priority queue of simulation events."""
from __future__ import annotations

import heapq
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Event model ───────────────────────────────────────────────────────────────

class SimEventType:
    SESSION_START  = "session_start"
    SESSION_END    = "session_end"
    BAR            = "bar"
    ORDER_CHECK    = "order_check"
    EOD            = "eod"
    CUSTOM         = "custom"


@dataclass(order=True)
class SimEvent:
    """A single simulation event, sortable by timestamp + priority."""
    timestamp:  float            = field(compare=True)
    priority:   int              = field(compare=True, default=5)   # lower = earlier
    event_type: str              = field(compare=False, default=SimEventType.BAR)
    payload:    dict[str, Any]   = field(compare=False, default_factory=dict)
    event_id:   str              = field(compare=False, default_factory=lambda: str(uuid.uuid4()))


# ── Scheduler ─────────────────────────────────────────────────────────────────

class EventScheduler:
    """
    Min-heap priority queue of SimEvents.

    Events at equal timestamps are ordered by priority (lower first).
    Typical priorities:
        1 – SESSION_START / SESSION_END
        3 – ORDER_CHECK
        5 – BAR
        8 – EOD
    """

    def __init__(self) -> None:
        self._heap: list[SimEvent] = []
        self._count: int = 0

    def schedule(self, event: SimEvent) -> None:
        heapq.heappush(self._heap, event)
        self._count += 1

    def schedule_bar(self, timestamp: float, symbol: str, bar_index: int) -> None:
        self.schedule(SimEvent(
            timestamp  = timestamp,
            priority   = 5,
            event_type = SimEventType.BAR,
            payload    = {"symbol": symbol, "bar_index": bar_index},
        ))

    def next_event(self) -> Optional[SimEvent]:
        if self._heap:
            return heapq.heappop(self._heap)
        return None

    def peek(self) -> Optional[SimEvent]:
        return self._heap[0] if self._heap else None

    def clear(self) -> None:
        self._heap.clear()
        self._count = 0

    def pending_count(self) -> int:
        return len(self._heap)

    def total_scheduled(self) -> int:
        return self._count
