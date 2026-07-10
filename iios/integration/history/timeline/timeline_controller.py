"""iios/integration/history/timeline/timeline_controller.py

Orchestrates timeline navigation and drives event delivery.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from iios.integration.history.history_constants import TimelineDirection, TimelineStatus
from iios.integration.history.history_exceptions import TimelineNotActiveError, TimelineSeekError
from iios.integration.history.timeline.timeline       import Timeline
from iios.integration.history.timeline.timeline_event import TimelineEvent

logger = logging.getLogger(__name__)


class TimelineController:
    """
    Controls traversal and event delivery for one Timeline.

    The controller drives a cursor through the timeline at the configured
    speed, delivering events to all registered handlers.
    """

    def __init__(self, timeline: Timeline, speed_multiplier: float = 1.0) -> None:
        self._timeline = timeline
        self._speed    = speed_multiplier
        self._paused   = False
        self._stopped  = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def play(
        self,
        start_ts: float | None = None,
        end_ts:   float | None = None,
        direction: TimelineDirection = TimelineDirection.FORWARD,
    ) -> None:
        """
        Drive event delivery from start_ts to end_ts (or timeline bounds).
        """
        lo, hi = self._timeline.time_range()
        start  = start_ts if start_ts is not None else lo
        end    = end_ts   if end_ts   is not None else hi

        cursor = self._timeline.cursor()
        cursor.direction       = direction
        cursor.start_ts        = start
        cursor.end_ts          = end
        cursor.current_ts      = start if direction == TimelineDirection.FORWARD else end
        cursor.speed_multiplier = self._speed
        cursor.status          = TimelineStatus.ACTIVE

        events = self._timeline.events_in_range(start, end)
        if direction == TimelineDirection.REVERSE:
            events = list(reversed(events))

        prev_ts   = events[0].timestamp if events else start
        prev_wall = time.monotonic()

        for event in events:
            if self._stopped:
                break
            while self._paused and not self._stopped:
                await asyncio.sleep(0.05)

            # Speed-controlled delay
            if self._speed > 0:
                sim_delta  = abs(event.timestamp - prev_ts)
                wall_delay = sim_delta / self._speed
                if wall_delay > 0:
                    elapsed   = time.monotonic() - prev_wall
                    remaining = wall_delay - elapsed
                    if remaining > 0:
                        await asyncio.sleep(remaining)

            cursor.current_ts = event.timestamp
            self._timeline._dispatch(event)
            self._timeline._stats.on_event()

            prev_ts   = event.timestamp
            prev_wall = time.monotonic()

        if not self._stopped:
            cursor.status = TimelineStatus.STOPPED
            self._timeline._stats.finalize()

    def pause(self) -> None:
        self._paused = True
        self._timeline.cursor().status = TimelineStatus.PAUSED
        self._timeline._stats.on_pause()

    def resume(self) -> None:
        self._paused = False
        self._timeline.cursor().status = TimelineStatus.ACTIVE

    def stop(self) -> None:
        self._stopped = True
        self._timeline.cursor().status = TimelineStatus.STOPPED

    def seek(self, target_ts: float) -> None:
        self._timeline.seek(target_ts)

    def set_speed(self, speed: float) -> None:
        self._speed = speed
        self._timeline.cursor().speed_multiplier = speed

    def timeline(self) -> Timeline:
        return self._timeline
