"""iios/integration/history/historical_data_engine.py

Top-level singleton facade for the Historical Data & Replay Framework.

Usage:
    engine = get_historical_data_engine(auto_start=True)
    dataset = engine.create_dataset(...)
    engine.ingest(dataset.dataset_id, record)
    records = asyncio.run(engine.query(f))
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from iios.integration.history.core.historical_dataset  import HistoricalDataset
from iios.integration.history.core.historical_record   import HistoricalRecord
from iios.integration.history.core.historical_snapshot import HistoricalSnapshot
from iios.integration.history.history_constants        import (
    DEFAULT_CACHE_MAX_RECORDS,
    DEFAULT_CACHE_TTL_SEC,
    DEFAULT_MAX_DATASETS,
    DEFAULT_MAX_QUERY_RESULTS,
    DEFAULT_QUERY_TIMEOUT_SEC,
    HISTORY_ENGINE_VERSION,
    HistoricalDataType,
    HistoryEngineStatus,
    ReplayMode,
    ReplayType,
    SimulationMode,
)
from iios.integration.history.history_exceptions       import (
    HistoryEngineAlreadyRunningError,
    HistoryEngineInitializationError,
    HistoryEngineNotRunningError,
)
from iios.integration.history.history_factory          import HistoryFactory
from iios.integration.history.history_manager          import HistoryManager
from iios.integration.history.history_registry         import HistoryRegistry
from iios.integration.history.query.historical_filter  import HistoricalFilter
from iios.integration.history.replay.replay_engine     import ReplayEngine
from iios.integration.history.simulation.scenario_loader import Scenario

logger = logging.getLogger(__name__)


class HistoricalDataEngine:
    """
    Top-level facade for the Historical Data & Replay Framework.

    Lifecycle:
        await engine.start()      # initialise internals
        ...use engine...
        await engine.stop()       # graceful shutdown
    """

    def __init__(self) -> None:
        self._status    = HistoryEngineStatus.STOPPED
        self._started_at: float | None = None
        self._manager:  HistoryManager | None = None
        self._replay:   ReplayEngine   | None = None
        self._factory   = HistoryFactory()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._status == HistoryEngineStatus.RUNNING:
            raise HistoryEngineAlreadyRunningError("Engine already running.")
        self._status = HistoryEngineStatus.INITIALIZING
        try:
            backend  = HistoryFactory.create_storage_backend()
            registry = HistoryFactory.create_registry()
            index    = HistoryFactory.create_index_manager()
            cache    = HistoryFactory.create_cache()
            query    = HistoryFactory.create_query_engine(backend)
            self._replay  = HistoryFactory.create_replay_engine()
            self._manager = HistoryManager(
                registry=registry,
                backend=backend,
                index_manager=index,
                query_engine=query,
                cache=cache,
            )
            self._status     = HistoryEngineStatus.RUNNING
            self._started_at = time.time()
            logger.info(
                "[HistoricalDataEngine] Started (v%s).", HISTORY_ENGINE_VERSION
            )
        except Exception as exc:
            self._status = HistoryEngineStatus.ERROR
            raise HistoryEngineInitializationError(
                f"Initialisation failed: {exc}"
            ) from exc

    async def stop(self) -> None:
        if self._status not in (HistoryEngineStatus.RUNNING, HistoryEngineStatus.ERROR):
            return
        self._status = HistoryEngineStatus.STOPPING
        logger.info("[HistoricalDataEngine] Stopped.")
        self._status      = HistoryEngineStatus.STOPPED
        self._started_at  = None

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self._status != HistoryEngineStatus.RUNNING:
            raise HistoryEngineNotRunningError(
                f"Engine is not running (status={self._status.value})."
            )

    # ── Dataset API ───────────────────────────────────────────────────────────

    def create_dataset(self, dataset: HistoricalDataset) -> HistoricalDataset:
        self._assert_running()
        return self._manager.create_dataset(dataset)  # type: ignore[union-attr]

    def get_dataset(self, dataset_id: str) -> HistoricalDataset:
        self._assert_running()
        return self._manager.get_dataset(dataset_id)  # type: ignore[union-attr]

    def list_datasets(
        self,
        data_type: HistoricalDataType | None = None,
    ) -> list[HistoricalDataset]:
        self._assert_running()
        return self._manager.list_datasets(data_type=data_type)  # type: ignore[union-attr]

    def delete_dataset(self, dataset_id: str) -> None:
        self._assert_running()
        self._manager.delete_dataset(dataset_id)  # type: ignore[union-attr]

    # ── Ingestion API ─────────────────────────────────────────────────────────

    def ingest(self, dataset_id: str, record: HistoricalRecord) -> None:
        self._assert_running()
        self._manager.ingest(dataset_id, record)  # type: ignore[union-attr]

    def ingest_batch(
        self,
        dataset_id: str,
        records:    list[HistoricalRecord],
    ) -> int:
        self._assert_running()
        return self._manager.ingest_batch(dataset_id, records)  # type: ignore[union-attr]

    # ── Query API ─────────────────────────────────────────────────────────────

    async def query(
        self,
        f:         HistoricalFilter,
        use_cache: bool = True,
    ) -> list[HistoricalRecord]:
        self._assert_running()
        return await self._manager.query(f, use_cache=use_cache)  # type: ignore[union-attr]

    # ── Replay API ────────────────────────────────────────────────────────────

    def start_replay(
        self,
        dataset_ids:     list[str],
        start_ts:        float,
        end_ts:          float,
        speed_multiplier: float = 1.0,
        symbols:         list[str] | None = None,
        data_type:       HistoricalDataType = HistoricalDataType.MARKET_DATA,
    ) -> str:
        """Create a replay session. Returns session_id."""
        self._assert_running()
        session = self._replay.create_session(  # type: ignore[union-attr]
            replay_type      = ReplayType.FULL_SYSTEM,
            data_type        = data_type,
            dataset_ids      = dataset_ids,
            symbols          = symbols or [],
            start_ts         = start_ts,
            end_ts           = end_ts,
            speed_multiplier = speed_multiplier,
            mode             = ReplayMode.FORWARD,
        )
        return session.session_id

    # ── Simulation API ────────────────────────────────────────────────────────

    def create_simulation(self, scenario: Scenario) -> "SimulationController":  # noqa: F821
        self._assert_running()
        return HistoryFactory.create_simulation_controller(
            backend       = self._manager._backend,  # type: ignore[union-attr]
            replay_engine = self._replay,
        )

    async def run_scenario(self, scenario: Scenario) -> None:
        """Build a SimulationController and run the scenario."""
        self._assert_running()
        ctrl = self.create_simulation(scenario)
        await ctrl.run(scenario)

    # ── Snapshot API ─────────────────────────────────────────────────────────

    def create_snapshot(self, dataset_id: str) -> HistoricalSnapshot:
        self._assert_running()
        return self._manager.create_snapshot(dataset_id)  # type: ignore[union-attr]

    # ── Status / Stats ────────────────────────────────────────────────────────

    def is_running(self) -> bool:
        return self._status == HistoryEngineStatus.RUNNING

    def status(self) -> HistoryEngineStatus:
        return self._status

    def uptime_sec(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def stats(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "version":    HISTORY_ENGINE_VERSION,
            "status":     self._status.value,
            "uptime_sec": self.uptime_sec(),
        }
        if self._manager:
            base["manager"] = self._manager.stats()
        return base


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: HistoricalDataEngine | None = None
_lock = threading.Lock()


def get_historical_data_engine(
    auto_start: bool = False,
) -> HistoricalDataEngine:
    global _instance
    with _lock:
        if _instance is None:
            _instance = HistoricalDataEngine()
    if auto_start and not _instance.is_running():
        asyncio.run(_instance.start())
    return _instance


def reset_historical_data_engine() -> None:
    global _instance
    with _lock:
        _instance = None
