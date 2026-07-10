"""iios/integration/history/simulation/simulation_controller.py

Orchestrates one simulation run end-to-end.

Wires together:
  - ScenarioLoader (scenario config)
  - DatasetLoader  (data retrieval)
  - SimulationClock (virtual time)
  - ReplayEngine   (event delivery)
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable

from iios.integration.history.core.historical_record    import HistoricalRecord
from iios.integration.history.history_constants         import (
    HistoricalDataType,
    ReplayMode,
    ReplayType,
    SimulationMode,
    SimulationStatus,
    DEFAULT_REPLAY_SPEED,
)
from iios.integration.history.history_exceptions        import (
    SimulationError,
    SimulationNotActiveError,
)
from iios.integration.history.replay.replay_engine      import ReplayEngine
from iios.integration.history.simulation.dataset_loader import DatasetLoader
from iios.integration.history.simulation.scenario_loader import Scenario
from iios.integration.history.simulation.simulation_clock import SimulationClock

logger = logging.getLogger(__name__)

RecordHandler = Callable[[HistoricalRecord], None]


class SimulationController:
    """
    Top-level simulation orchestrator.

    Usage:
        ctrl = SimulationController(dataset_loader, replay_engine)
        ctrl.on_record(my_handler)
        await ctrl.run(scenario)
    """

    def __init__(
        self,
        dataset_loader: DatasetLoader,
        replay_engine:  ReplayEngine,
    ) -> None:
        self._loader        = dataset_loader
        self._replay        = replay_engine
        self._clock:        SimulationClock | None = None
        self._status        = SimulationStatus.IDLE
        self._session_id:   str | None = None
        self._handlers:     list[RecordHandler] = []
        self._stats: dict[str, Any] = {
            "simulations_run":    0,
            "records_processed":  0,
            "errors":             0,
        }

    # ── Handler registration ──────────────────────────────────────────────────

    def on_record(self, handler: RecordHandler) -> None:
        self._handlers.append(handler)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def run(self, scenario: Scenario) -> None:
        """
        Execute one simulation scenario synchronously (awaited by caller).
        """
        if self._status == SimulationStatus.RUNNING:
            raise SimulationError("Simulation already running.")

        self._status = SimulationStatus.RUNNING
        self._clock  = SimulationClock(
            start_ts         = scenario.start_ts,
            speed_multiplier = scenario.speed_multiplier or 0,
            tick_size_sec    = 1.0,
        )

        # Load records
        try:
            records = await self._loader.load_multi(
                dataset_ids = scenario.dataset_ids,
                start_ts    = scenario.start_ts,
                end_ts      = scenario.end_ts,
                symbols     = scenario.symbols or None,
            )
        except Exception as exc:
            self._status = SimulationStatus.ERROR
            self._stats["errors"] += 1
            logger.error("[SimulationController] Data loading failed: %s", exc)
            raise SimulationError(f"Data loading failed: {exc}") from exc

        # Create replay session
        session = self._replay.create_session(
            replay_type      = ReplayType.FULL_SYSTEM,
            data_type        = HistoricalDataType.CUSTOM,
            dataset_ids      = scenario.dataset_ids,
            symbols          = scenario.symbols,
            start_ts         = scenario.start_ts,
            end_ts           = scenario.end_ts,
            speed_multiplier = scenario.speed_multiplier,
            mode             = ReplayMode.FORWARD,
            description      = f"Scenario: {scenario.name}",
        )
        self._session_id = session.session_id

        # Wire handlers
        for h in self._handlers:
            self._replay.on_record(session.session_id, h)

        # Run replay
        try:
            await self._replay.start_replay(session.session_id, records)
            self._status = SimulationStatus.COMPLETED
            self._stats["simulations_run"]   += 1
            self._stats["records_processed"] += session.records_replayed
            logger.info(
                "[SimulationController] Scenario '%s' completed: %d records.",
                scenario.name, session.records_replayed,
            )
        except Exception as exc:
            self._status = SimulationStatus.ERROR
            self._stats["errors"] += 1
            logger.error("[SimulationController] Simulation error: %s", exc)
            raise

    def pause(self) -> None:
        if self._status != SimulationStatus.RUNNING:
            raise SimulationNotActiveError("No active simulation to pause.")
        if self._clock:
            self._clock.pause()
        if self._session_id:
            self._replay.pause(self._session_id)
        self._status = SimulationStatus.PAUSED

    def resume(self) -> None:
        if self._status != SimulationStatus.PAUSED:
            raise SimulationNotActiveError("Simulation is not paused.")
        if self._clock:
            self._clock.resume()
        if self._session_id:
            self._replay.resume(self._session_id)
        self._status = SimulationStatus.RUNNING

    def stop(self) -> None:
        if self._session_id:
            self._replay.stop(self._session_id)
        if self._clock:
            self._clock.pause()
        self._status = SimulationStatus.COMPLETED

    def clock(self) -> SimulationClock | None:
        return self._clock

    def status(self) -> SimulationStatus:
        return self._status

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
