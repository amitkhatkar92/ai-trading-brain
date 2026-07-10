"""iios/integration/history/timeline/timeline_cursor.py

Cursor that tracks the current position on a timeline.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import TimelineDirection, TimelineStatus


@dataclass
class TimelineCursor:
    """
    Represents the current replay position and traversal state.

    The cursor supports:
      - Forward / reverse traversal
      - Pause / resume
      - Seek to arbitrary timestamp
      - Variable speed multiplier
    """

    cursor_id:         str               = field(default_factory=lambda: str(uuid.uuid4()))
    timeline_id:       str               = ""
    current_ts:        float             = 0.0
    start_ts:          float             = 0.0
    end_ts:            float             = 0.0
    speed_multiplier:  float             = 1.0
    direction:         TimelineDirection = TimelineDirection.FORWARD
    status:            TimelineStatus    = TimelineStatus.IDLE
    events_visited:    int               = 0
    created_at:        float             = field(default_factory=time.time)
    last_moved_at:     float             = 0.0
    metadata:          dict[str, Any]    = field(default_factory=dict)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_at_start(self) -> bool:
        return self.current_ts <= self.start_ts

    def is_at_end(self) -> bool:
        return self.current_ts >= self.end_ts

    def is_active(self) -> bool:
        return self.status == TimelineStatus.ACTIVE

    def progress(self) -> float:
        span = self.end_ts - self.start_ts
        if span <= 0:
            return 0.0
        return min(1.0, max(0.0, (self.current_ts - self.start_ts) / span))

    def move(self, delta_sec: float) -> float:
        """
        Advance (or retreat) cursor by ``delta_sec`` seconds.
        Returns the new current_ts.
        """
        if self.direction == TimelineDirection.REVERSE:
            self.current_ts -= delta_sec
        else:
            self.current_ts += delta_sec
        self.current_ts  = max(self.start_ts, min(self.end_ts, self.current_ts))
        self.last_moved_at = time.time()
        self.events_visited += 1
        return self.current_ts

    def seek(self, target_ts: float) -> float:
        self.status     = TimelineStatus.SEEKING
        self.current_ts = max(self.start_ts, min(self.end_ts, target_ts))
        self.status     = TimelineStatus.ACTIVE
        return self.current_ts

    def to_dict(self) -> dict[str, Any]:
        return {
            "cursor_id":        self.cursor_id,
            "timeline_id":      self.timeline_id,
            "current_ts":       self.current_ts,
            "speed_multiplier": self.speed_multiplier,
            "direction":        self.direction.value,
            "status":           self.status.value,
            "progress":         round(self.progress(), 4),
        }
