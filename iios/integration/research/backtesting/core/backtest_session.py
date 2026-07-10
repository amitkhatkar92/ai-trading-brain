"""core/backtest_session.py — Tracks simulation execution state."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import SimulationStatus


@dataclass
class BacktestSession:
    """
    Ephemeral execution context for one simulation run.

    Created when a backtest starts running, updated bar-by-bar,
    discarded once BacktestResult is persisted.
    """

    backtest_id:       str             = ""
    session_id:        str             = field(default_factory=lambda: str(uuid.uuid4()))
    status:            SimulationStatus = SimulationStatus.IDLE

    # ── Progress ──────────────────────────────────────────────────────────────
    current_bar_index: int             = 0
    total_bars:        int             = 0
    current_timestamp: float           = 0.0

    # ── Timing ────────────────────────────────────────────────────────────────
    started_at:        Optional[float] = None
    ended_at:          Optional[float] = None
    last_checkpoint:   Optional[float] = None

    error_message:     Optional[str]   = None
    created_at:        float           = field(default_factory=time.time)

    # ── State transitions ─────────────────────────────────────────────────────

    def start(self, total_bars: int = 0) -> None:
        self.status         = SimulationStatus.RUNNING
        self.started_at     = time.time()
        self.total_bars     = total_bars
        self.current_bar_index = 0

    def end(self, *, failed: bool = False, aborted: bool = False) -> None:
        self.ended_at = time.time()
        if aborted:
            self.status = SimulationStatus.ABORTED
        elif failed:
            self.status = SimulationStatus.FAILED
        else:
            self.status = SimulationStatus.COMPLETED

    def advance(self, bar_index: int, timestamp: float) -> None:
        self.current_bar_index = bar_index
        self.current_timestamp = timestamp

    def progress(self) -> float:
        """Return completion fraction 0.0–1.0."""
        if self.total_bars <= 0:
            return 0.0
        return min(1.0, self.current_bar_index / self.total_bars)

    def is_active(self) -> bool:
        return self.status in (SimulationStatus.RUNNING, SimulationStatus.PAUSED)

    def duration_sec(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at if self.ended_at is not None else time.time()
        return end - self.started_at

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":        self.session_id,
            "backtest_id":       self.backtest_id,
            "status":            self.status.value,
            "current_bar_index": self.current_bar_index,
            "total_bars":        self.total_bars,
            "current_timestamp": self.current_timestamp,
            "progress":          self.progress(),
            "started_at":        self.started_at,
            "ended_at":          self.ended_at,
            "duration_sec":      self.duration_sec(),
            "error_message":     self.error_message,
        }
