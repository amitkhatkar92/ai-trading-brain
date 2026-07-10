"""iios/integration/research/research_factory.py

Factory for all research framework components.
"""
from __future__ import annotations

from iios.integration.research.core.research_history       import ResearchHistory
from iios.integration.research.datasets.dataset_manager    import DatasetManager
from iios.integration.research.experiments.experiment_lifecycle import ExperimentLifecycle
from iios.integration.research.experiments.experiment_runner    import ExperimentRunner
from iios.integration.research.monitoring.research_monitor  import ResearchMonitor
from iios.integration.research.projects.project_manager     import ProjectManager
from iios.integration.research.registry.experiment_registry import ExperimentRegistry
from iios.integration.research.research_constants           import (
    DEFAULT_MAX_DATASETS,
    DEFAULT_MAX_EXPERIMENTS,
    DEFAULT_MAX_HISTORY_ENTRIES,
    DEFAULT_MAX_PROJECTS,
    DEFAULT_EXPERIMENT_TIMEOUT_SEC,
)
from iios.integration.research.research_registry            import ResearchRegistry
from iios.integration.research.tracking.execution_tracker   import ExecutionTracker
from iios.integration.research.workflow.research_workflow    import ResearchWorkflow, WorkflowStep


class ResearchFactory:
    """Constructs all major research framework objects."""

    @staticmethod
    def create_registry(max_projects: int = DEFAULT_MAX_PROJECTS) -> ResearchRegistry:
        return ResearchRegistry(max_projects=max_projects)

    @staticmethod
    def create_project_manager(max_projects: int = DEFAULT_MAX_PROJECTS) -> ProjectManager:
        return ProjectManager(max_projects=max_projects)

    @staticmethod
    def create_experiment_registry(
        max_experiments: int = DEFAULT_MAX_EXPERIMENTS,
    ) -> ExperimentRegistry:
        return ExperimentRegistry(max_experiments=max_experiments)

    @staticmethod
    def create_experiment_lifecycle() -> ExperimentLifecycle:
        return ExperimentLifecycle()

    @staticmethod
    def create_experiment_runner() -> ExperimentRunner:
        return ExperimentRunner()

    @staticmethod
    def create_dataset_manager(max_datasets: int = DEFAULT_MAX_DATASETS) -> DatasetManager:
        return DatasetManager(max_datasets=max_datasets)

    @staticmethod
    def create_execution_tracker() -> ExecutionTracker:
        return ExecutionTracker()

    @staticmethod
    def create_research_monitor(
        timeout_sec: float = DEFAULT_EXPERIMENT_TIMEOUT_SEC,
    ) -> ResearchMonitor:
        return ResearchMonitor(timeout_sec=timeout_sec)

    @staticmethod
    def create_research_history(
        max_entries: int = DEFAULT_MAX_HISTORY_ENTRIES,
    ) -> ResearchHistory:
        return ResearchHistory(max_entries=max_entries)

    @staticmethod
    def create_workflow(
        project_id:  str = "",
        name:        str = "",
        description: str = "",
    ) -> ResearchWorkflow:
        return ResearchWorkflow(
            project_id  = project_id,
            name        = name,
            description = description,
        )

    @staticmethod
    def create_workflow_step(
        name:          str       = "",
        experiment_id: str       = "",
        depends_on:    list[str] | None = None,
    ) -> WorkflowStep:
        return WorkflowStep(
            name          = name,
            experiment_id = experiment_id,
            depends_on    = depends_on or [],
        )
