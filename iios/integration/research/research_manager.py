"""iios/integration/research/research_manager.py

High-level coordinator for all research operations.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from iios.integration.research.core.research_dataset     import ResearchDataset
from iios.integration.research.core.research_experiment  import ResearchExperiment
from iios.integration.research.core.research_history     import ResearchHistory, ResearchHistoryEntry
from iios.integration.research.core.research_project     import ResearchProject
from iios.integration.research.core.research_result      import ResearchResult
from iios.integration.research.core.research_statistics  import ResearchStatistics
from iios.integration.research.datasets.dataset_manager  import DatasetManager
from iios.integration.research.experiments.experiment_lifecycle import ExperimentLifecycle
from iios.integration.research.experiments.experiment_runner    import ExperimentRunner
from iios.integration.research.monitoring.research_monitor import ResearchMonitor
from iios.integration.research.projects.project_manager   import ProjectManager
from iios.integration.research.registry.experiment_registry import ExperimentRegistry
from iios.integration.research.research_constants         import (
    ExperimentStatus,
    ResearchEventType,
    ResearchProjectStatus,
)
from iios.integration.research.research_context           import ResearchContext
from iios.integration.research.research_exceptions        import (
    ResearchExperimentNotFoundError,
    ResearchProjectNotFoundError,
)
from iios.integration.research.research_registry          import ResearchRegistry
from iios.integration.research.tracking.execution_tracker import ExecutionTracker

logger = logging.getLogger(__name__)


class ResearchManager:
    """
    Unified coordinator for all research operations.

    Owns:
    - ResearchRegistry (projects)
    - ProjectManager (project lifecycle)
    - ExperimentRegistry (experiments)
    - ExperimentLifecycle (state machine)
    - ExperimentRunner (execution)
    - DatasetManager (datasets)
    - ExecutionTracker (checkpoints / progress)
    - ResearchMonitor (health)
    - ResearchHistory (audit log)
    """

    def __init__(
        self,
        registry:    ResearchRegistry,
        proj_mgr:    ProjectManager,
        exp_registry: ExperimentRegistry,
        lifecycle:   ExperimentLifecycle,
        runner:      ExperimentRunner,
        dataset_mgr: DatasetManager,
        tracker:     ExecutionTracker,
        monitor:     ResearchMonitor,
        history:     ResearchHistory,
    ) -> None:
        self._registry   = registry
        self._proj_mgr   = proj_mgr
        self._exp_reg    = exp_registry
        self._lifecycle  = lifecycle
        self._runner     = runner
        self._dataset_mgr = dataset_mgr
        self._tracker    = tracker
        self._monitor    = monitor
        self._history    = history
        self._results:   dict[str, ResearchResult] = {}

    # ── Project API ───────────────────────────────────────────────────────────

    def create_project(self, project: ResearchProject) -> ResearchProject:
        with ResearchContext.scope("create_project", project_id=project.project_id):
            self._proj_mgr.create(project)
            self._registry.register(project)
            self._history.append(ResearchHistoryEntry(
                entity_type = "project",
                entity_id   = project.project_id,
                event_type  = ResearchEventType.PROJECT_CREATED,
                new_status  = project.status.value,
            ))
            logger.info("[ResearchManager] Created project '%s'.", project.name)
            return project

    def get_project(self, project_id: str) -> ResearchProject:
        return self._registry.get(project_id)

    def activate_project(self, project_id: str) -> ResearchProject:
        p = self._proj_mgr.activate(project_id)
        self._registry.update(p)
        return p

    def archive_project(self, project_id: str) -> ResearchProject:
        p = self._proj_mgr.archive(project_id)
        self._registry.update(p)
        self._history.append(ResearchHistoryEntry(
            entity_type = "project",
            entity_id   = project_id,
            event_type  = ResearchEventType.PROJECT_ARCHIVED,
            new_status  = ResearchProjectStatus.ARCHIVED.value,
        ))
        return p

    def complete_project(self, project_id: str) -> ResearchProject:
        p = self._proj_mgr.complete(project_id)
        self._registry.update(p)
        self._history.append(ResearchHistoryEntry(
            entity_type = "project",
            entity_id   = project_id,
            event_type  = ResearchEventType.PROJECT_COMPLETED,
            new_status  = ResearchProjectStatus.COMPLETED.value,
        ))
        return p

    def clone_project(self, project_id: str, new_name: str = "") -> ResearchProject:
        cloned = self._proj_mgr.clone(project_id, new_name=new_name)
        self._registry.register(cloned)
        self._history.append(ResearchHistoryEntry(
            entity_type = "project",
            entity_id   = cloned.project_id,
            event_type  = ResearchEventType.PROJECT_CREATED,
            new_status  = cloned.status.value,
            details     = {"cloned_from": project_id},
        ))
        return cloned

    def list_projects(self) -> list[ResearchProject]:
        return self._registry.all_projects()

    # ── Experiment API ────────────────────────────────────────────────────────

    def create_experiment(self, experiment: ResearchExperiment) -> ResearchExperiment:
        with ResearchContext.scope(
            "create_experiment",
            project_id    = experiment.project_id,
            experiment_id = experiment.experiment_id,
        ):
            self._exp_reg.register(experiment)
            # Attach to project if known
            if experiment.project_id:
                try:
                    p = self._proj_mgr.get(experiment.project_id)
                    p.add_experiment(experiment.experiment_id)
                    self._proj_mgr.update(p)
                except ResearchProjectNotFoundError:
                    pass
            self._history.append(ResearchHistoryEntry(
                entity_type = "experiment",
                entity_id   = experiment.experiment_id,
                event_type  = ResearchEventType.EXPERIMENT_CREATED,
                new_status  = experiment.status.value,
            ))
            return experiment

    def get_experiment(self, experiment_id: str) -> ResearchExperiment:
        return self._exp_reg.get(experiment_id)

    def configure_experiment(self, experiment_id: str) -> ResearchExperiment:
        exp = self._exp_reg.get(experiment_id)
        self._lifecycle.configure(exp)
        self._exp_reg.update(exp)
        return exp

    def queue_experiment(self, experiment_id: str) -> ResearchExperiment:
        exp = self._exp_reg.get(experiment_id)
        self._lifecycle.queue(exp)
        self._exp_reg.update(exp)
        return exp

    async def run_experiment(
        self,
        experiment_id: str,
        fn:            Callable,
        *args: Any,
        **kwargs: Any,
    ) -> ResearchResult:
        exp = self._exp_reg.get(experiment_id)
        self._monitor.record_start(experiment_id)
        self._history.append(ResearchHistoryEntry(
            entity_type = "experiment",
            entity_id   = experiment_id,
            event_type  = ResearchEventType.EXPERIMENT_STARTED,
            old_status  = exp.status.value,
            new_status  = ExperimentStatus.RUNNING.value,
        ))

        with ResearchContext.scope(
            "run_experiment",
            experiment_id = experiment_id,
            project_id    = exp.project_id,
        ):
            result = await self._runner.run(exp, fn, *args, **kwargs)

        self._results[result.result_id] = result
        self._exp_reg.update(exp)
        self._monitor.record_end(experiment_id, exp.status.value)
        self._history.append(ResearchHistoryEntry(
            entity_type = "experiment",
            entity_id   = experiment_id,
            event_type  = (
                ResearchEventType.EXPERIMENT_COMPLETED
                if result.is_success
                else ResearchEventType.EXPERIMENT_FAILED
            ),
            new_status  = exp.status.value,
        ))
        self._history.append(ResearchHistoryEntry(
            entity_type = "experiment",
            entity_id   = experiment_id,
            event_type  = ResearchEventType.RESULT_RECORDED,
            details     = {"result_id": result.result_id},
        ))
        return result

    def pause_experiment(self, experiment_id: str) -> ResearchExperiment:
        exp = self._exp_reg.get(experiment_id)
        self._lifecycle.pause(exp)
        self._exp_reg.update(exp)
        self._history.append(ResearchHistoryEntry(
            entity_type = "experiment",
            entity_id   = experiment_id,
            event_type  = ResearchEventType.EXPERIMENT_PAUSED,
            new_status  = ExperimentStatus.PAUSED.value,
        ))
        return exp

    def resume_experiment(self, experiment_id: str) -> ResearchExperiment:
        exp = self._exp_reg.get(experiment_id)
        self._lifecycle.resume(exp)
        self._exp_reg.update(exp)
        self._history.append(ResearchHistoryEntry(
            entity_type = "experiment",
            entity_id   = experiment_id,
            event_type  = ResearchEventType.EXPERIMENT_RESUMED,
            new_status  = ExperimentStatus.RUNNING.value,
        ))
        return exp

    def cancel_experiment(self, experiment_id: str) -> ResearchExperiment:
        exp = self._exp_reg.get(experiment_id)
        self._lifecycle.cancel(exp)
        self._exp_reg.update(exp)
        self._history.append(ResearchHistoryEntry(
            entity_type = "experiment",
            entity_id   = experiment_id,
            event_type  = ResearchEventType.EXPERIMENT_CANCELLED,
            new_status  = ExperimentStatus.CANCELLED.value,
        ))
        return exp

    def archive_experiment(self, experiment_id: str) -> ResearchExperiment:
        exp = self._exp_reg.get(experiment_id)
        self._lifecycle.archive(exp)
        self._exp_reg.update(exp)
        self._history.append(ResearchHistoryEntry(
            entity_type = "experiment",
            entity_id   = experiment_id,
            event_type  = ResearchEventType.EXPERIMENT_ARCHIVED,
            new_status  = ExperimentStatus.ARCHIVED.value,
        ))
        return exp

    def compare_experiments(
        self,
        experiment_ids: list[str],
    ) -> dict[str, Any]:
        """Compare metrics across multiple experiments."""
        comparison: dict[str, Any] = {
            "experiment_ids": experiment_ids,
            "experiments":    {},
            "metrics":        {},
        }
        for eid in experiment_ids:
            exp = self._exp_reg.get(eid)
            comparison["experiments"][eid] = exp.to_dict()
            # Find result
            result = self._get_result_for_experiment(eid)
            comparison["metrics"][eid] = result.metrics if result else {}
        return comparison

    def _get_result_for_experiment(self, experiment_id: str) -> ResearchResult | None:
        exp = self._exp_reg.get(experiment_id)
        if exp.result_id:
            return self._results.get(exp.result_id)
        return None

    def get_result(self, result_id: str) -> ResearchResult | None:
        return self._results.get(result_id)

    # ── Dataset API ───────────────────────────────────────────────────────────

    def register_dataset(self, dataset: ResearchDataset) -> ResearchDataset:
        result = self._dataset_mgr.register(dataset)
        self._history.append(ResearchHistoryEntry(
            entity_type = "dataset",
            entity_id   = dataset.dataset_id,
            event_type  = ResearchEventType.DATASET_REGISTERED,
            new_status  = dataset.status.value,
        ))
        return result

    def get_dataset(self, dataset_id: str) -> ResearchDataset:
        return self._dataset_mgr.get(dataset_id)

    def new_dataset_version(
        self,
        source_dataset_id: str,
        changes: str = "",
    ) -> ResearchDataset:
        return self._dataset_mgr.new_version(source_dataset_id, changes=changes)

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        stat = ResearchStatistics.compute(
            projects    = self._registry.all_projects(),
            experiments = self._exp_reg.all_experiments(),
            datasets    = self._dataset_mgr.all_datasets(),
            results     = list(self._results.values()),
        )
        return {
            **stat.to_dict(),
            "history_entries":    self._history.count(),
            "monitor":            self._monitor.health(),
        }
