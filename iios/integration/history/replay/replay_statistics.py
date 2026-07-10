"""iios/integration/history/replay/replay_statistics.py

Aggregated performance statistics for a replay session.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReplayStatistics:
    stat_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    session_id:       str   = ""
    total_records:    int   = 0
    records_per_sec:  float = 0.0
    elapsed_sec:      float = 0.0
    paused_sec:       float = 0.0
    errors:           int   = 0
    skipped:          int   = 0
    wall_start:       float = field(default_factory=time.time)
    wall_end:         float = 0.0
    datasets_read:    int   = 0
    partitions_read:  int   = 0
    cache_hits:       int   = 0
    computed_at:      float = field(default_factory=time.time)

    def update(self, records_delta: int = 0) -> None:
        self.total_records += records_delta
        elapsed = time.time() - self.wall_start
        if elapsed > 0:
            self.records_per_sec = self.total_records / elapsed
        self.elapsed_sec = elapsed

    def finalize(self) -> None:
        self.wall_end    = time.time()
        self.elapsed_sec = self.wall_end - self.wall_start
        if self.elapsed_sec > 0:
            self.records_per_sec = self.total_records / self.elapsed_sec
        self.computed_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_id":         self.stat_id,
            "session_id":      self.session_id,
            "total_records":   self.total_records,
            "records_per_sec": round(self.records_per_sec, 1),
            "elapsed_sec":     round(self.elapsed_sec, 3),
            "errors":          self.errors,
            "skipped":         self.skipped,
            "cache_hits":      self.cache_hits,
            "computed_at":     self.computed_at,
        }
