"""iios/integration/history/timeline/timeline.py

The Timeline — an ordered, seekable sequence of TimelineEvents.

The timeline is the in-memory representation of a historical data stream.
Events are sorted by (timestamp, priority) for deterministic ordering.
"""
from __future__ import annotations

import bisect
import logging
import threading
import time
import uuid
from typing import Any, Callable

from iios.integration.history.history_constants import (
    MAX_TIMELINE_EVENTS,
    HistoricalDataType,
    TimelineDirection,
    TimelineStatus,
)
from iios.integration.history.history_exceptions import (
    TimelineNotActiveError,
    TimelineOverflowError,
    TimelineSeekError,
)
from iios.integration.history.timeline.timeline_cursor     import TimelineCursor
from iios.integration.history.timeline.timeline_event      import TimelineEvent
from iios.integration.history.timeline.timeline_statistics import TimelineStatistics

logger = logging.getLogger(__name__)

EventHandler = Callable[[TimelineEvent], None]


class Timeline:
    """
    Ordered, thread-safe event timeline.

    Supports:
    - append / bulk load
    - forward and reverse traversal
    - seek to any timestamp
    - speed-controlled iteration
    - pause / resume
    - fan-out to multiple handlers
    """

    def __init__(
        self,
        timeline_id:  str   = "",
        max_events:   int   = MAX_TIMELINE_EVENTS,
    ) -> None:
        self.timeline_id = timeline_id or str(uuid.uuid4())
        self._max        = max_events
        self._lock       = threading.RLock()
        self._events:    list[TimelineEvent]   = []   # sorted by (timestamp, -priority)
        self._ts_keys:   list[float]           = []   # parallel list for bisect
        self._cursor:    TimelineCursor        = TimelineCursor(timeline_id=self.timeline_id)
        self._stats:     TimelineStatistics    = TimelineStatistics(timeline_id=self.timeline_id)
        self._handlers:  list[EventHandler]   = []

    # ── Event management ──────────────────────────────────────────────────────

    def append(self, event: TimelineEvent) -> None:
        with self._lock:
            if len(self._events) >= self._max:
                raise TimelineOverflowError(
                    f"Timeline '{self.timeline_id}' is full ({self._max} events)."
                )
            event.timeline_id = self.timeline_id
            pos = bisect.bisect_right(self._ts_keys, event.timestamp)
            self._events.insert(pos, event)
            self._ts_keys.insert(pos, event.timestamp)
            self._stats.total_events += 1

    def bulk_append(self, events: list[TimelineEvent]) -> int:
        """Append many events at once. Returns count appended."""
        count = 0
        for e in events:
            try:
                self.append(e)
                count += 1
            except TimelineOverflowError:
                break
        return count

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._ts_keys.clear()
            self._stats.total_events = 0

    # ── Traversal ─────────────────────────────────────────────────────────────

    def events_in_range(
        self,
        start_ts: float,
        end_ts:   float,
        subject:  str = "",
        data_type: HistoricalDataType | None = None,
        limit:    int = 0,
    ) -> list[TimelineEvent]:
        with self._lock:
            lo = bisect.bisect_left(self._ts_keys, start_ts)
            hi = bisect.bisect_right(self._ts_keys, end_ts)
            result = self._events[lo:hi]
            if subject:
                result = [e for e in result if e.subject == subject]
            if data_type:
                result = [e for e in result if e.data_type == data_type]
            if limit > 0:
                result = result[:limit]
            return result

    def next_event(self, after_ts: float) -> TimelineEvent | None:
        with self._lock:
            pos = bisect.bisect_right(self._ts_keys, after_ts)
            if pos < len(self._events):
                return self._events[pos]
            return None

    def prev_event(self, before_ts: float) -> TimelineEvent | None:
        with self._lock:
            pos = bisect.bisect_left(self._ts_keys, before_ts)
            if pos > 0:
                return self._events[pos - 1]
            return None

    # ── Cursor ────────────────────────────────────────────────────────────────

    def seek(self, target_ts: float) -> TimelineCursor:
        with self._lock:
            if self._ts_keys:
                lo = self._ts_keys[0]
                hi = self._ts_keys[-1]
                if not (lo <= target_ts <= hi):
                    raise TimelineSeekError(
                        f"Seek target {target_ts} is outside timeline range "
                        f"[{lo}, {hi}]."
                    )
                # Ensure cursor bounds reflect actual timeline span
                self._cursor.start_ts = lo
                self._cursor.end_ts   = hi
            self._cursor.seek(target_ts)
            self._stats.on_seek()
            return self._cursor

    def cursor(self) -> TimelineCursor:
        return self._cursor

    # ── Handlers ─────────────────────────────────────────────────────────────

    def on_event(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def _dispatch(self, event: TimelineEvent) -> None:
        for h in self._handlers:
            try:
                h(event)
            except Exception as exc:
                self._stats.errors += 1
                logger.warning("[Timeline] Handler error: %s", exc)

    # ── State ─────────────────────────────────────────────────────────────────

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def time_range(self) -> tuple[float, float]:
        with self._lock:
            if not self._ts_keys:
                return 0.0, 0.0
            return self._ts_keys[0], self._ts_keys[-1]

    def statistics(self) -> TimelineStatistics:
        return self._stats

    def to_dict(self) -> dict[str, Any]:
        lo, hi = self.time_range()
        return {
            "timeline_id": self.timeline_id,
            "event_count": self.event_count(),
            "start_ts":    lo,
            "end_ts":      hi,
            "cursor":      self._cursor.to_dict(),
        }
