"""iios/integration/history/replay/replay_controller.py

High-level controller that orchestrates one replay session:
  1. Loads records from storage (via query engine)
  2. Feeds them through ReplayScheduler
  3. Publishes each record to registered handlers
  4. Updates ReplaySession state
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable

from iios.integration.history.core.historical_record    import HistoricalRecord
from iios.integration.history.history_constants         import ReplayMode, ReplayStatus
from iios.integration.history.history_exceptions        import (
    ReplayAlreadyActiveError,
    ReplayNotActiveError,
    ReplayTimeRangeError,
)
from iios.integration.history.replay.replay_scheduler   import ReplayScheduler
from iios.integration.history.replay.replay_session     import ReplaySession
from iios.integration.history.replay.replay_statistics  import ReplayStatistics

logger = logging.getLogger(__name__)

RecordHandler = Callable[[HistoricalRecord], None]


class ReplayController:
    """
    Controls one ReplaySession lifecycle.

    The controller is not tied to a specific data source; it accepts a
    pre-fetched (or lazy-loaded) list of records to replay.
    """

    def __init__(self, session: ReplaySession) -> None:
        self._session   = session
        self._scheduler = ReplayScheduler(session.speed_multiplier)
        self._stats     = ReplayStatistics(session_id=session.session_id)
        self._lock      = threading.RLock()
        self._handlers: list[RecordHandler] = []
        self._task:     asyncio.Task | None = None

    # ── Handler registration ──────────────────────────────────────────────────

    def on_record(self, handler: RecordHandler) -> None:
        """Register a callback to receive each replayed record."""
        self._handlers.append(handler)

    # ── Control ───────────────────────────────────────────────────────────────

    async def start(self, records: list[HistoricalRecord]) -> None:
        """Begin replay of ``records`` (already sorted by timestamp)."""
        if self._session.is_active():
            raise ReplayAlreadyActiveError(
                f"Session '{self._session.session_id}' is already active."
            )
        if self._session.start_ts >= self._session.end_ts:
            raise ReplayTimeRangeError("end_ts must be greater than start_ts.")

        # Validate direction
        if self._session.mode == ReplayMode.REVERSE:
            records = list(reversed(records))

        self._session.start()
        self._scheduler.reset()
        self._stats.wall_start = time.time()
        logger.info(
            "[ReplayController] Starting session '%s' (%d records, %.1f×).",
            self._session.session_id, len(records), self._session.speed_multiplier,
        )

        try:
            async for record in self._scheduler.schedule(records):
                self._session.current_ts  = record.timestamp
                self._session.records_replayed += 1
                self._stats.update(records_delta=1)
                self._dispatch(record)

                if self._session.status == ReplayStatus.STOPPED:
                    break
        except Exception as exc:
            self._session.status = ReplayStatus.ERROR
            self._stats.errors   += 1
            logger.error("[ReplayController] Error in session '%s': %s", self._session.session_id, exc)
            raise
        else:
            if self._session.status != ReplayStatus.STOPPED:
                self._session.complete()

        self._stats.finalize()
        logger.info(
            "[ReplayController] Session '%s' completed: %d records in %.2fs.",
            self._session.session_id,
            self._session.records_replayed,
            self._stats.elapsed_sec,
        )

    def pause(self) -> None:
        if not self._session.is_active():
            raise ReplayNotActiveError("No active replay to pause.")
        self._session.pause()
        self._scheduler.pause()

    def resume(self) -> None:
        if self._session.status != ReplayStatus.PAUSED:
            raise ReplayNotActiveError("Replay is not paused.")
        self._session.resume()
        self._scheduler.resume()

    def stop(self) -> None:
        self._session.stop()
        self._scheduler.stop()

    def set_speed(self, speed: float) -> None:
        self._session.speed_multiplier = speed
        self._scheduler.set_speed(speed)

    def seek(self, target_ts: float) -> None:
        """Update current_ts for a seek operation (records are re-filtered externally)."""
        self._session.current_ts = target_ts

    # ── Access ────────────────────────────────────────────────────────────────

    def session(self)  -> ReplaySession:    return self._session
    def statistics(self) -> ReplayStatistics: return self._stats

    # ── Internal ─────────────────────────────────────────────────────────────

    def _dispatch(self, record: HistoricalRecord) -> None:
        for h in self._handlers:
            try:
                h(record)
            except Exception as exc:
                self._stats.errors += 1
                logger.warning("[ReplayController] Handler error: %s", exc)
