"""iios/integration/history/history_factory.py

Factory that constructs all major historical data framework components.
"""
from __future__ import annotations

from iios.integration.history.analytics.history_analytics      import HistoryAnalytics
from iios.integration.history.cache                             import HistoryCache
from iios.integration.history.compression                       import DataCompressor
from iios.integration.history.history_constants                 import (
    DEFAULT_CACHE_MAX_RECORDS,
    DEFAULT_CACHE_TTL_SEC,
    DEFAULT_MAX_DATASETS,
    DEFAULT_QUERY_TIMEOUT_SEC,
    DEFAULT_MAX_QUERY_RESULTS,
    DEFAULT_REPLAY_SPEED,
)
from iios.integration.history.history_registry                  import HistoryRegistry
from iios.integration.history.indexing.dataset_index            import DatasetIndexManager
from iios.integration.history.query.dataset_selector            import DatasetSelector
from iios.integration.history.query.historical_filter           import HistoricalFilter
from iios.integration.history.query.historical_search           import HistoricalSearch
from iios.integration.history.query.query_engine                import QueryEngine
from iios.integration.history.replay.replay_engine              import ReplayEngine
from iios.integration.history.simulation.dataset_loader         import DatasetLoader
from iios.integration.history.simulation.scenario_loader        import ScenarioLoader
from iios.integration.history.simulation.simulation_controller  import SimulationController
from iios.integration.history.storage.storage_backend           import (
    InMemoryStorageBackend,
    StorageBackend,
)
from iios.integration.history.timeline.timeline                 import Timeline
from iios.integration.history.timeline.timeline_controller      import TimelineController


class HistoryFactory:
    """
    Centralised factory for all historical data framework objects.
    """

    @staticmethod
    def create_storage_backend(max_records: int = 10_000_000) -> InMemoryStorageBackend:
        return InMemoryStorageBackend(max_records=max_records)

    @staticmethod
    def create_registry(max_datasets: int = DEFAULT_MAX_DATASETS) -> HistoryRegistry:
        return HistoryRegistry(max_datasets=max_datasets)

    @staticmethod
    def create_index_manager() -> DatasetIndexManager:
        return DatasetIndexManager()

    @staticmethod
    def create_cache(
        max_size: int = DEFAULT_CACHE_MAX_RECORDS,
        ttl_sec:  int = DEFAULT_CACHE_TTL_SEC,
    ) -> HistoryCache:
        return HistoryCache(max_size=max_size, ttl_sec=ttl_sec)

    @staticmethod
    def create_compressor() -> DataCompressor:
        return DataCompressor()

    @staticmethod
    def create_query_engine(
        backend:     StorageBackend,
        timeout_sec: float = DEFAULT_QUERY_TIMEOUT_SEC,
        max_results: int   = DEFAULT_MAX_QUERY_RESULTS,
    ) -> QueryEngine:
        return QueryEngine(
            backend=backend,
            selector=DatasetSelector(),
            search=HistoricalSearch(),
            timeout_sec=timeout_sec,
            max_results=max_results,
        )

    @staticmethod
    def create_replay_engine() -> ReplayEngine:
        return ReplayEngine()

    @staticmethod
    def create_dataset_loader(backend: StorageBackend) -> DatasetLoader:
        return DatasetLoader(backend=backend)

    @staticmethod
    def create_scenario_loader() -> ScenarioLoader:
        return ScenarioLoader()

    @staticmethod
    def create_simulation_controller(
        backend: StorageBackend,
        replay_engine: ReplayEngine | None = None,
    ) -> SimulationController:
        loader = DatasetLoader(backend=backend)
        engine = replay_engine or ReplayEngine()
        return SimulationController(dataset_loader=loader, replay_engine=engine)

    @staticmethod
    def create_timeline(timeline_id: str = "") -> Timeline:
        return Timeline(timeline_id=timeline_id)

    @staticmethod
    def create_timeline_controller(
        timeline: Timeline,
        speed_multiplier: float = 1.0,
    ) -> TimelineController:
        return TimelineController(timeline=timeline, speed_multiplier=speed_multiplier)

    @staticmethod
    def create_analytics() -> HistoryAnalytics:
        return HistoryAnalytics()
