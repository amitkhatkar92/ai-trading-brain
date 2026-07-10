"""iios/integration/research/research_engine.py

Top-level singleton facade for the Quantitative Research Framework.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable

from iios.integration.research.core.research_dataset     import ResearchDataset
from iios.integration.research.core.research_experiment  import ResearchExperiment
from iios.integration.research.core.research_project     import ResearchProject
from iios.integration.research.core.research_result      import ResearchResult
from iios.integration.research.research_constants         import (
    RESEARCH_ENGINE_VERSION,
    ResearchEngineStatus,
)
from iios.integration.research.research_exceptions        import (
    ResearchEngineAlreadyRunningError,
    ResearchEngineInitializationError,
    ResearchEngineNotRunningError,
)
from iios.integration.research.research_factory           import ResearchFactory
from iios.integration.research.research_manager           import ResearchManager

logger = logging.getLogger(__name__)


class ResearchEngine:
    """
    Top-level singleton facade for the Quantitative Research Framework.

    Lifecycle:
        await engine.start()
        ...
        await engine.stop()
    """

    def __init__(self) -> None:
        self._status    = ResearchEngineStatus.STOPPED
        self._manager:  ResearchManager | None = None
        self._started_at: float | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._status == ResearchEngineStatus.RUNNING:
            raise ResearchEngineAlreadyRunningError("Research engine is already running.")
        self._status = ResearchEngineStatus.INITIALIZING
        try:
            registry   = ResearchFactory.create_registry()
            proj_mgr   = ResearchFactory.create_project_manager()
            exp_reg    = ResearchFactory.create_experiment_registry()
            lifecycle  = ResearchFactory.create_experiment_lifecycle()
            runner     = ResearchFactory.create_experiment_runner()
            dataset_mgr = ResearchFactory.create_dataset_manager()
            tracker    = ResearchFactory.create_execution_tracker()
            monitor    = ResearchFactory.create_research_monitor()
            history    = ResearchFactory.create_research_history()
            self._manager = ResearchManager(
                registry    = registry,
                proj_mgr    = proj_mgr,
                exp_registry = exp_reg,
                lifecycle   = lifecycle,
                runner      = runner,
                dataset_mgr = dataset_mgr,
                tracker     = tracker,
                monitor     = monitor,
                history     = history,
            )
            self._status     = ResearchEngineStatus.RUNNING
            self._started_at = time.time()
            logger.info("[ResearchEngine] Started (v%s).", RESEARCH_ENGINE_VERSION)
        except Exception as exc:
            self._status = ResearchEngineStatus.ERROR
            raise ResearchEngineInitializationError(f"Initialization failed: {exc}") from exc

    async def stop(self) -> None:
        if self._status not in (ResearchEngineStatus.RUNNING, ResearchEngineStatus.ERROR):
            return
        self._status     = ResearchEngineStatus.STOPPING
        logger.info("[ResearchEngine] Stopped.")
        self._status     = ResearchEngineStatus.STOPPED
        self._started_at = None

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self._status != ResearchEngineStatus.RUNNING:
            raise ResearchEngineNotRunningError(
                f"Research engine is not running (status={self._status.value})."
            )

    # ── Project API ───────────────────────────────────────────────────────────

    def create_project(self, project: ResearchProject) -> ResearchProject:
        self._assert_running()
        return self._manager.create_project(project)  # type: ignore[union-attr]

    def get_project(self, project_id: str) -> ResearchProject:
        self._assert_running()
        return self._manager.get_project(project_id)  # type: ignore[union-attr]

    def clone_project(self, project_id: str, new_name: str = "") -> ResearchProject:
        self._assert_running()
        return self._manager.clone_project(project_id, new_name=new_name)  # type: ignore[union-attr]

    def archive_project(self, project_id: str) -> ResearchProject:
        self._assert_running()
        return self._manager.archive_project(project_id)  # type: ignore[union-attr]

    def list_projects(self) -> list[ResearchProject]:
        self._assert_running()
        return self._manager.list_projects()  # type: ignore[union-attr]

    # ── Experiment API ────────────────────────────────────────────────────────

    def create_experiment(self, experiment: ResearchExperiment) -> ResearchExperiment:
        self._assert_running()
        return self._manager.create_experiment(experiment)  # type: ignore[union-attr]

    def get_experiment(self, experiment_id: str) -> ResearchExperiment:
        self._assert_running()
        return self._manager.get_experiment(experiment_id)  # type: ignore[union-attr]

    def configure_experiment(self, experiment_id: str) -> ResearchExperiment:
        self._assert_running()
        return self._manager.configure_experiment(experiment_id)  # type: ignore[union-attr]

    def queue_experiment(self, experiment_id: str) -> ResearchExperiment:
        self._assert_running()
        return self._manager.queue_experiment(experiment_id)  # type: ignore[union-attr]

    async def run_experiment(
        self,
        experiment_id: str,
        fn:            Callable,
        *args: Any,
        **kwargs: Any,
    ) -> ResearchResult:
        self._assert_running()
        return await self._manager.run_experiment(experiment_id, fn, *args, **kwargs)  # type: ignore[union-attr]

    def pause_experiment(self, experiment_id: str) -> ResearchExperiment:
        self._assert_running()
        return self._manager.pause_experiment(experiment_id)  # type: ignore[union-attr]

    def resume_experiment(self, experiment_id: str) -> ResearchExperiment:
        self._assert_running()
        return self._manager.resume_experiment(experiment_id)  # type: ignore[union-attr]

    def cancel_experiment(self, experiment_id: str) -> ResearchExperiment:
        self._assert_running()
        return self._manager.cancel_experiment(experiment_id)  # type: ignore[union-attr]

    def archive_experiment(self, experiment_id: str) -> ResearchExperiment:
        self._assert_running()
        return self._manager.archive_experiment(experiment_id)  # type: ignore[union-attr]

    def compare_experiments(self, experiment_ids: list[str]) -> dict[str, Any]:
        self._assert_running()
        return self._manager.compare_experiments(experiment_ids)  # type: ignore[union-attr]

    # ── Dataset API ───────────────────────────────────────────────────────────

    def register_dataset(self, dataset: ResearchDataset) -> ResearchDataset:
        self._assert_running()
        return self._manager.register_dataset(dataset)  # type: ignore[union-attr]

    def get_dataset(self, dataset_id: str) -> ResearchDataset:
        self._assert_running()
        return self._manager.get_dataset(dataset_id)  # type: ignore[union-attr]

    # ── Status / Stats ────────────────────────────────────────────────────────

    def is_running(self) -> bool:
        return self._status == ResearchEngineStatus.RUNNING

    def status(self) -> ResearchEngineStatus:
        return self._status

    def uptime_sec(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def stats(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "version":    RESEARCH_ENGINE_VERSION,
            "status":     self._status.value,
            "uptime_sec": self.uptime_sec(),
        }
        if self._manager:
            base["manager"] = self._manager.stats()
        return base


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: ResearchEngine | None = None
_lock = threading.Lock()


def get_research_engine(auto_start: bool = False) -> ResearchEngine:
    global _instance
    with _lock:
        if _instance is None:
            _instance = ResearchEngine()
    if auto_start and not _instance.is_running():
        asyncio.run(_instance.start())
    return _instance


def reset_research_engine() -> None:
    global _instance
    with _lock:
        _instance = None
