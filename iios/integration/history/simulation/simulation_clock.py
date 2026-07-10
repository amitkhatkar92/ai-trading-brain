"""iios/integration/history/simulation/simulation_clock.py

Controllable simulation clock.

Provides a ``simulated_time`` that advances independently from wall-clock
time, with configurable speed multiplier and pause/resume support.

Used by simulation_controller, backtesting consumers, and paper-trading
consumers to keep all components synchronised to the same virtual time.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_exceptions import SimulationClockError


class SimulationClock:
    """
    Deterministic simulation clock.

    Clients call ``tick()`` to advance the clock by one step, or set the
    time directly via ``set_time()``.  ``now()`` always returns the current
    simulated timestamp (POSIX UTC).
    """

    def __init__(
        self,
        start_ts:         float = 0.0,
        speed_multiplier: float = 1.0,
        tick_size_sec:    float = 1.0,
    ) -> None:
        if speed_multiplier < 0:
            raise SimulationClockError(f"Speed multiplier must be ≥ 0, got {speed_multiplier}.")
        self.clock_id         = str(uuid.uuid4())
        self._simulated_time  = start_ts if start_ts > 0 else time.time()
        self._speed           = speed_multiplier
        self._tick_size       = tick_size_sec
        self._is_paused       = False
        self._ticks           = 0
        self._wall_start      = time.time()
        self._paused_at: float | None = None
        self._pause_elapsed   = 0.0

    # ── Properties ────────────────────────────────────────────────────────────

    def now(self) -> float:
        """Current simulated timestamp."""
        if self._is_paused:
            return self._simulated_time
        wall_elapsed = time.time() - self._wall_start - self._pause_elapsed
        return self._simulated_time + wall_elapsed * self._speed

    def ticks(self) -> int:
        return self._ticks

    def is_paused(self) -> bool:
        return self._is_paused

    # ── Control ───────────────────────────────────────────────────────────────

    def tick(self) -> float:
        """Advance by one tick_size_sec. Returns new simulated time."""
        if self._is_paused:
            return self._simulated_time
        self._simulated_time += self._tick_size * self._speed
        self._ticks           += 1
        return self._simulated_time

    def set_time(self, ts: float) -> None:
        """Jump to a specific simulated timestamp."""
        self._simulated_time = ts
        self._wall_start     = time.time()
        self._pause_elapsed  = 0.0

    def pause(self) -> None:
        if not self._is_paused:
            self._is_paused  = True
            self._paused_at  = time.time()
            self._simulated_time = self.now()

    def resume(self) -> None:
        if self._is_paused and self._paused_at is not None:
            self._pause_elapsed += time.time() - self._paused_at
            self._is_paused      = False
            self._paused_at      = None

    def set_speed(self, speed: float) -> None:
        if speed < 0:
            raise SimulationClockError(f"Speed multiplier must be ≥ 0, got {speed}.")
        current = self.now()
        self._speed          = speed
        self._simulated_time = current
        self._wall_start     = time.time()
        self._pause_elapsed  = 0.0

    def reset(self, start_ts: float | None = None) -> None:
        self._simulated_time = start_ts if start_ts is not None else time.time()
        self._wall_start     = time.time()
        self._pause_elapsed  = 0.0
        self._is_paused      = False
        self._ticks          = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "clock_id":        self.clock_id,
            "simulated_time":  self.now(),
            "speed":           self._speed,
            "tick_size_sec":   self._tick_size,
            "ticks":           self._ticks,
            "is_paused":       self._is_paused,
        }
