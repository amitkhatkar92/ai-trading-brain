"""engine/simulation_clock.py — Deterministic simulation time-keeper."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from iios.integration.research.backtesting.backtest_exceptions import SimulationClockError


@dataclass
class SimulationClock:
    """
    Manages simulated time for a single backtest run.

    All timestamps are unix epoch floats.
    The clock does NOT wall-clock sleep; it advances in discrete steps.
    """

    _current_ts:  float  = field(default=0.0, init=False)
    _start_ts:    float  = field(default=0.0, init=False)
    _end_ts:      float  = field(default=0.0, init=False)
    _tick_count:  int    = field(default=0, init=False)
    _initialised: bool   = field(default=False, init=False)

    # ── Initialisation ────────────────────────────────────────────────────────

    def initialise(self, start_ts: float, end_ts: float) -> None:
        if start_ts >= end_ts:
            raise SimulationClockError(
                f"start_ts ({start_ts}) must be < end_ts ({end_ts})"
            )
        self._start_ts   = start_ts
        self._end_ts     = end_ts
        self._current_ts = start_ts
        self._tick_count = 0
        self._initialised = True

    def reset(self) -> None:
        self._current_ts  = self._start_ts
        self._tick_count  = 0

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def current(self) -> float:
        return self._current_ts

    @property
    def start(self) -> float:
        return self._start_ts

    @property
    def end(self) -> float:
        return self._end_ts

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def is_initialised(self) -> bool:
        return self._initialised

    # ── Advancement ──────────────────────────────────────────────────────────

    def advance_to(self, timestamp: float) -> None:
        """Set clock to a specific timestamp (must be ≥ current)."""
        if not self._initialised:
            raise SimulationClockError("Clock must be initialised before advancing")
        if timestamp < self._current_ts:
            raise SimulationClockError(
                f"Cannot move clock backward: {timestamp} < {self._current_ts}"
            )
        self._current_ts = timestamp
        self._tick_count += 1

    def is_within_range(self, timestamp: float) -> bool:
        return self._start_ts <= timestamp <= self._end_ts

    def remaining_fraction(self) -> float:
        total = self._end_ts - self._start_ts
        if total <= 0:
            return 0.0
        done = self._current_ts - self._start_ts
        return 1.0 - min(1.0, done / total)

    def to_dict(self) -> dict:
        return {
            "current_ts":  self._current_ts,
            "start_ts":    self._start_ts,
            "end_ts":      self._end_ts,
            "tick_count":  self._tick_count,
            "initialised": self._initialised,
        }
