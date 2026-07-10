"""iios/integration/history/replay/replay_scheduler.py

Schedules replay events in wall-clock time according to the speed multiplier.

The scheduler converts simulated timestamps to wall-clock delays so that
replaying at 2× speed plays events at half the real-world interval.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, AsyncGenerator

from iios.integration.history.core.historical_record import HistoricalRecord
from iios.integration.history.history_constants import MAX_REPLAY_SPEED, MIN_REPLAY_SPEED
from iios.integration.history.history_exceptions import ReplaySpeedError

logger = logging.getLogger(__name__)

RecordCallback = Callable[[HistoricalRecord], None]


class ReplayScheduler:
    """
    Async replay tick generator.

    Given a sorted list of records, yields them in order,
    sleeping between yields according to ``speed_multiplier``.

    speed_multiplier > 1 = faster than real-time
    speed_multiplier = 0 = as fast as possible (no sleeping)
    """

    def __init__(self, speed_multiplier: float = 1.0) -> None:
        self.set_speed(speed_multiplier)
        self._paused    = False
        self._stop_flag = False

    def set_speed(self, speed: float) -> None:
        if speed < 0:
            raise ReplaySpeedError(f"Speed must be ≥ 0, got {speed}.")
        if speed > MAX_REPLAY_SPEED:
            raise ReplaySpeedError(f"Speed {speed} exceeds MAX_REPLAY_SPEED={MAX_REPLAY_SPEED}.")
        self._speed = speed

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stop_flag = True

    def reset(self) -> None:
        self._stop_flag = False
        self._paused    = False

    async def schedule(
        self,
        records: list[HistoricalRecord],
    ) -> AsyncGenerator[HistoricalRecord, None]:
        """
        Async generator that yields records in timestamp order.

        If speed_multiplier == 0: yield as fast as possible.
        Otherwise: sleep proportionally between events.
        """
        if not records:
            return

        prev_sim_ts  = records[0].timestamp
        prev_wall_ts = time.monotonic()

        for record in records:
            # Check stop flag
            if self._stop_flag:
                break

            # Handle pause: poll until unpaused
            while self._paused and not self._stop_flag:
                await asyncio.sleep(0.05)

            if self._stop_flag:
                break

            # Compute expected wall-clock delay
            if self._speed > 0:
                sim_delta  = record.timestamp - prev_sim_ts
                wall_delay = sim_delta / self._speed
                if wall_delay > 0:
                    elapsed = time.monotonic() - prev_wall_ts
                    remaining = wall_delay - elapsed
                    if remaining > 0:
                        await asyncio.sleep(remaining)

            yield record

            prev_sim_ts  = record.timestamp
            prev_wall_ts = time.monotonic()
