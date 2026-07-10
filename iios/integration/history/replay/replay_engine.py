"""iios/integration/history/replay/replay_engine.py

Top-level facade for all replay operations.

Manages multiple concurrent ReplaySession objects and provides a uniform API
for the rest of IIOS to start, pause, stop and monitor replays.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable

from iios.integration.history.core.historical_record   import HistoricalRecord
from iios.integration.history.history_constants        import (
    HistoricalDataType,
    ReplayMode,
    ReplayType,
    DEFAULT_REPLAY_SPEED,
)
from iios.integration.history.history_exceptions       import (
    ReplayAlreadyActiveError,
    ReplaySessionNotFoundError,
)
from iios.integration.history.replay.replay_controller import ReplayController, RecordHandler
from iios.integration.history.replay.replay_session    import ReplaySession
from iios.integration.history.replay.replay_statistics import ReplayStatistics

logger = logging.getLogger(__name__)


class ReplayEngine:
    """
    Multi-session replay engine.

    Each ``start_replay()`` call creates a new ReplaySession and its
    associated ReplayController.  Sessions run concurrently on the event loop.
    """

    def __init__(self) -> None:
        self._lock:        threading.RLock = threading.RLock()
        self._sessions:    dict[str, ReplayController] = {}
        self._stats: dict[str, int] = {
            "sessions_created":   0,
            "sessions_completed": 0,
            "sessions_errored":   0,
        }

    # ── Session management ────────────────────────────────────────────────────

    def create_session(
        self,
        replay_type:      ReplayType         = ReplayType.MARKET,
        data_type:        HistoricalDataType  = HistoricalDataType.MARKET_DATA,
        dataset_ids:      list[str]           | None = None,
        symbols:          list[str]           | None = None,
        start_ts:         float               = 0.0,
        end_ts:           float               = 0.0,
        speed_multiplier: float               = DEFAULT_REPLAY_SPEED,
        mode:             ReplayMode          = ReplayMode.FORWARD,
        description:      str                 = "",
    ) -> ReplaySession:
        session = ReplaySession(
            replay_type      = replay_type,
            data_type        = data_type,
            dataset_ids      = dataset_ids or [],
            symbols          = symbols or [],
            start_ts         = start_ts,
            end_ts           = end_ts,
            speed_multiplier = speed_multiplier,
            mode             = mode,
            description      = description,
        )
        ctrl = ReplayController(session)
        with self._lock:
            self._sessions[session.session_id] = ctrl
            self._stats["sessions_created"] += 1
        return session

    def get_session(self, session_id: str) -> ReplaySession:
        with self._lock:
            ctrl = self._sessions.get(session_id)
            if ctrl is None:
                raise ReplaySessionNotFoundError(f"Session '{session_id}' not found.")
            return ctrl.session()

    def get_controller(self, session_id: str) -> ReplayController:
        with self._lock:
            ctrl = self._sessions.get(session_id)
            if ctrl is None:
                raise ReplaySessionNotFoundError(f"Session '{session_id}' not found.")
            return ctrl

    def on_record(self, session_id: str, handler: RecordHandler) -> None:
        self.get_controller(session_id).on_record(handler)

    async def start_replay(
        self,
        session_id: str,
        records:    list[HistoricalRecord],
    ) -> None:
        ctrl = self.get_controller(session_id)
        try:
            await ctrl.start(records)
            self._stats["sessions_completed"] += 1
        except Exception:
            self._stats["sessions_errored"] += 1
            raise

    def pause(self, session_id: str) -> None:
        self.get_controller(session_id).pause()

    def resume(self, session_id: str) -> None:
        self.get_controller(session_id).resume()

    def stop(self, session_id: str) -> None:
        self.get_controller(session_id).stop()

    def set_speed(self, session_id: str, speed: float) -> None:
        self.get_controller(session_id).set_speed(speed)

    def statistics(self, session_id: str) -> ReplayStatistics:
        return self.get_controller(session_id).statistics()

    def active_sessions(self) -> list[ReplaySession]:
        with self._lock:
            return [c.session() for c in self._sessions.values() if c.session().is_active()]

    def all_sessions(self) -> list[ReplaySession]:
        with self._lock:
            return [c.session() for c in self._sessions.values()]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                **self._stats,
                "active_sessions": len([c for c in self._sessions.values() if c.session().is_active()]),
                "total_sessions":  len(self._sessions),
            }
