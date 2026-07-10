"""iios/integration/history/timeline/timeline_statistics.py

Aggregated metrics for a timeline session.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimelineStatistics:
    stat_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    timeline_id:       str   = ""
    total_events:      int   = 0
    events_delivered:  int   = 0
    events_skipped:    int   = 0
    seeks:             int   = 0
    pauses:            int   = 0
    errors:            int   = 0
    elapsed_sec:       float = 0.0
    events_per_sec:    float = 0.0
    wall_start:        float = field(default_factory=time.time)
    computed_at:       float = field(default_factory=time.time)

    def on_event(self) -> None:
        self.events_delivered += 1
        elapsed = time.time() - self.wall_start
        if elapsed > 0:
            self.events_per_sec = self.events_delivered / elapsed

    def on_seek(self) -> None:
        self.seeks += 1

    def on_pause(self) -> None:
        self.pauses += 1

    def finalize(self) -> None:
        self.elapsed_sec = time.time() - self.wall_start
        if self.elapsed_sec > 0:
            self.events_per_sec = self.events_delivered / self.elapsed_sec
        self.computed_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_id":          self.stat_id,
            "timeline_id":      self.timeline_id,
            "total_events":     self.total_events,
            "events_delivered": self.events_delivered,
            "events_per_sec":   round(self.events_per_sec, 1),
            "seeks":            self.seeks,
            "pauses":           self.pauses,
            "elapsed_sec":      round(self.elapsed_sec, 3),
        }
