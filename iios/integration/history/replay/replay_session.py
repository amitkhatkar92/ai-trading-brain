"""iios/integration/history/replay/replay_session.py

State of one replay run.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import (
    HistoricalDataType,
    ReplayMode,
    ReplayStatus,
    ReplayType,
)


@dataclass
class ReplaySession:
    """
    Encapsulates all mutable state for one replay session.

    A session may replay one or many datasets simultaneously.
    ``current_ts`` tracks the virtual replay clock; ``speed_multiplier``
    controls how many real seconds per simulated second.
    """

    session_id:         str                = field(default_factory=lambda: str(uuid.uuid4()))
    replay_type:        ReplayType         = ReplayType.MARKET
    data_type:          HistoricalDataType = HistoricalDataType.MARKET_DATA
    dataset_ids:        list[str]          = field(default_factory=list)
    symbols:            list[str]          = field(default_factory=list)
    start_ts:           float              = 0.0
    end_ts:             float              = 0.0
    current_ts:         float              = 0.0
    speed_multiplier:   float              = 1.0    # 1.0 = realtime
    mode:               ReplayMode         = ReplayMode.FORWARD
    status:             ReplayStatus       = ReplayStatus.IDLE
    records_replayed:   int                = 0
    records_skipped:    int                = 0
    errors:             int                = 0
    started_at:         float              = 0.0
    paused_at:          float              = 0.0
    ended_at:           float              = 0.0
    description:        str                = ""
    metadata:           dict[str, Any]     = field(default_factory=dict)

    # ── Lifecycle helpers ──────────────────────────────────────────────────────

    def start(self) -> None:
        self.status     = ReplayStatus.RUNNING
        self.started_at = time.time()
        self.current_ts = self.start_ts

    def pause(self) -> None:
        self.status   = ReplayStatus.PAUSED
        self.paused_at = time.time()

    def resume(self) -> None:
        self.status    = ReplayStatus.RUNNING
        self.paused_at = 0.0

    def stop(self) -> None:
        self.status   = ReplayStatus.STOPPED
        self.ended_at = time.time()

    def complete(self) -> None:
        self.status   = ReplayStatus.COMPLETED
        self.ended_at = time.time()

    def elapsed_sec(self) -> float:
        if self.started_at == 0.0:
            return 0.0
        end = self.ended_at if self.ended_at > 0 else time.time()
        return end - self.started_at

    def progress(self) -> float:
        """0.0 – 1.0 progress through time range."""
        span = self.end_ts - self.start_ts
        if span <= 0:
            return 0.0
        return min(1.0, (self.current_ts - self.start_ts) / span)

    def is_active(self) -> bool:
        return self.status in (ReplayStatus.RUNNING, ReplayStatus.PAUSED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":       self.session_id,
            "replay_type":      self.replay_type.value,
            "data_type":        self.data_type.value,
            "start_ts":         self.start_ts,
            "end_ts":           self.end_ts,
            "current_ts":       self.current_ts,
            "speed_multiplier": self.speed_multiplier,
            "mode":             self.mode.value,
            "status":           self.status.value,
            "records_replayed": self.records_replayed,
            "progress":         round(self.progress(), 4),
            "elapsed_sec":      round(self.elapsed_sec(), 2),
        }
