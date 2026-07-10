"""learning_engine.py — Singleton facade for the AI Learning & Model Training Framework."""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    DEFAULT_MAX_JOBS,
    DEFAULT_MAX_MODELS,
    LearningEngineStatus,
    LearningType,
    ModelTask,
)
from iios.integration.research.learning.learning_exceptions import (
    EngineAlreadyRunningError,
    EngineNotRunningError,
    EngineInitializationError,
    ModelNotFoundError,
)
from iios.integration.research.learning.learning_registry import LearningRegistry
from iios.integration.research.learning.core.learning_configuration import LearningConfiguration
from iios.integration.research.learning.core.training_result        import TrainingResult
from iios.integration.research.learning.core.experiment             import Experiment
from iios.integration.research.learning.core.learning_history       import LearningHistory, LearningHistoryEntry
from iios.integration.research.learning.datasets.training_dataset   import TrainingDataset
from iios.integration.research.learning.datasets.dataset_registry   import DatasetRegistry
from iios.integration.research.learning.features.feature_engine     import FeatureEngine
from iios.integration.research.learning.models.model_metadata       import ModelMetadata
from iios.integration.research.learning.models.model_registry       import ModelRegistry
from iios.integration.research.learning.training.training_job       import TrainingJob
from iios.integration.research.learning.training.training_engine    import TrainingEngine
from iios.integration.research.learning.training.training_scheduler import TrainingScheduler
from iios.integration.research.learning.training.checkpoint_manager import CheckpointManager
from iios.integration.research.learning.training.hyperparameter_manager import HyperparameterManager
from iios.integration.research.learning.evaluation.evaluation_engine import EvaluationEngine
from iios.integration.research.learning.evaluation.evaluation_report import EvaluationReport
from iios.integration.research.learning.deployment.deployment_engine import DeploymentEngine
from iios.integration.research.learning.deployment.deployment_registry import DeploymentRecord
from iios.integration.research.learning.deployment.deployment_policy   import DeploymentPolicy
from iios.integration.research.learning.learning_constants import DeploymentStrategy
from iios.integration.research.learning.drift.drift_detector   import DriftDetector
from iios.integration.research.learning.drift.alert_manager    import AlertManager
from iios.integration.research.learning.drift.data_monitor     import DataMonitor
from iios.integration.research.learning.monitoring.model_monitor       import ModelMonitor
from iios.integration.research.learning.monitoring.performance_monitor import PerformanceMonitor
from iios.integration.research.learning.experiments.experiment_tracker import ExperimentTracker


class LearningEngine:
    """
    Singleton facade that owns and wires all Learning Framework subsystems.

    Usage::

        engine = get_learning_engine()
        await engine.start()

        job = engine.create_job(model_id, dataset_id, config)
        result = await engine.run_job(job.job_id, model, dataset)
    """

    def __init__(self) -> None:
        # ── Subsystems ────────────────────────────────────────────────────────
        self._job_registry    = LearningRegistry()
        self._dataset_registry = DatasetRegistry()
        self._model_registry  = ModelRegistry()
        self._scheduler       = TrainingScheduler()
        self._training_engine = TrainingEngine()
        self._checkpoint_mgr  = CheckpointManager()
        self._eval_engine     = EvaluationEngine()
        self._feature_engine  = FeatureEngine()
        self._experiment_tracker = ExperimentTracker()
        self._alert_manager   = AlertManager()
        self._drift_detector  = DriftDetector()
        self._data_monitor    = DataMonitor(self._drift_detector, self._alert_manager)
        self._model_monitor   = ModelMonitor(self._alert_manager)
        self._perf_monitor    = PerformanceMonitor()
        self._deployment_engine = DeploymentEngine()
        self._history         = LearningHistory()

        # ── Engine state ──────────────────────────────────────────────────────
        self._status:     LearningEngineStatus = LearningEngineStatus.STOPPED
        self._started_at: Optional[float]      = None
        self._lock        = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        with self._lock:
            if self._status == LearningEngineStatus.RUNNING:
                raise EngineAlreadyRunningError("LearningEngine is already running")
            self._status = LearningEngineStatus.INITIALIZING
        try:
            self._started_at = time.time()
            with self._lock:
                self._status = LearningEngineStatus.RUNNING
            self._history.append(LearningHistoryEntry.create("engine", "engine", "started"))
        except Exception as exc:
            with self._lock:
                self._status = LearningEngineStatus.ERROR
            raise EngineInitializationError(str(exc)) from exc

    async def stop(self) -> None:
        with self._lock:
            if self._status != LearningEngineStatus.RUNNING:
                return
            self._status = LearningEngineStatus.STOPPING
        with self._lock:
            self._status = LearningEngineStatus.STOPPED
        self._history.append(LearningHistoryEntry.create("engine", "engine", "stopped"))

    def is_running(self) -> bool:
        with self._lock:
            return self._status == LearningEngineStatus.RUNNING

    def status(self) -> LearningEngineStatus:
        with self._lock:
            return self._status

    def uptime_sec(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def _require_running(self) -> None:
        with self._lock:
            if self._status != LearningEngineStatus.RUNNING:
                raise EngineNotRunningError(
                    f"LearningEngine is not running (status={self._status.value})"
                )

    # ── Training jobs ─────────────────────────────────────────────────────────

    def create_job(
        self,
        model_id:           str,
        dataset_id:         str,
        config:             LearningConfiguration,
        *,
        job_id:             Optional[str]  = None,
        feature_pipeline_id: Optional[str] = None,
        learning_type:      LearningType   = LearningType.SUPERVISED,
        model_task:         ModelTask      = ModelTask.REGRESSION,
        experiment_id:      Optional[str]  = None,
        tags:               Optional[list] = None,
        priority:           int            = 5,
    ) -> TrainingJob:
        self._require_running()
        job = TrainingJob.create(
            model_id            = model_id,
            dataset_id          = dataset_id,
            config              = config,
            job_id              = job_id,
            feature_pipeline_id = feature_pipeline_id,
            learning_type       = learning_type,
            model_task          = model_task,
            experiment_id       = experiment_id,
            tags                = tags,
        )
        self._job_registry.register(job)
        self._scheduler.enqueue(job, priority=priority)
        if experiment_id:
            try:
                self._experiment_tracker.add_job(experiment_id, job.job_id)
            except Exception:
                pass
        self._history.append(
            LearningHistoryEntry.create("job", job.job_id, "created", {"model_id": model_id})
        )
        return job

    async def run_job(
        self,
        job_id:  str,
        model:   Any,    # BaseModel
        dataset: Any,    # TrainingDataset
    ) -> TrainingResult:
        self._require_running()
        job = self._job_registry.get(job_id)
        t0  = time.time()
        result = await self._training_engine.run_job(job, model, dataset)
        self._perf_monitor.record_job(time.time() - t0)
        self._history.append(
            LearningHistoryEntry.create("job", job_id, "completed", {"result_id": result.result_id})
        )
        # Update model metrics
        try:
            meta = self._model_registry.get(job.model_id)
            meta.mark_trained(job_id, result.metrics)
        except ModelNotFoundError:
            pass
        # Update experiment best
        if job.experiment_id:
            try:
                exp = self._experiment_tracker.get(job.experiment_id)
                metric_val = result.get_metric(exp.best_metric_name)
                self._experiment_tracker.update_best(job.experiment_id, job_id, metric_val)
            except Exception:
                pass
        return result

    def cancel_job(self, job_id: str) -> None:
        self._require_running()
        job = self._job_registry.get(job_id)
        job.cancel()
        self._history.append(LearningHistoryEntry.create("job", job_id, "cancelled"))

    def get_job(self, job_id: str) -> TrainingJob:
        return self._job_registry.get(job_id)

    def list_jobs(self, status=None) -> list[TrainingJob]:
        from iios.integration.research.learning.learning_constants import JobStatus
        st = status if isinstance(status, JobStatus) or status is None else JobStatus(status)
        return self._job_registry.all_jobs(status=st)

    # ── Models ────────────────────────────────────────────────────────────────

    def register_model(self, metadata: ModelMetadata) -> ModelMetadata:
        self._require_running()
        self._model_registry.register(metadata)
        self._history.append(
            LearningHistoryEntry.create("model", metadata.model_id, "registered")
        )
        return metadata

    def get_model(self, model_id: str) -> ModelMetadata:
        return self._model_registry.get(model_id)

    def list_models(self, task=None, status=None) -> list[ModelMetadata]:
        from iios.integration.research.learning.learning_constants import ModelStatus
        models = self._model_registry.all_models()
        if task is not None:
            task_val = task if isinstance(task, ModelTask) else ModelTask(task)
            models = [m for m in models if m.model_task == task_val]
        if status is not None:
            st_val = status if isinstance(status, ModelStatus) else ModelStatus(status)
            models = [m for m in models if m.status == st_val]
        return models

    # ── Datasets ──────────────────────────────────────────────────────────────

    def register_dataset(self, dataset: TrainingDataset) -> TrainingDataset:
        self._require_running()
        self._dataset_registry.register(dataset)
        return dataset

    def get_dataset(self, dataset_id: str) -> TrainingDataset:
        return self._dataset_registry.get(dataset_id)

    # ── Experiments ───────────────────────────────────────────────────────────

    def create_experiment(
        self,
        name:             str,
        model_task:       ModelTask,
        learning_type:    LearningType,
        **kwargs: Any,
    ) -> Experiment:
        self._require_running()
        return self._experiment_tracker.create_experiment(
            name, model_task, learning_type, **kwargs
        )

    def get_experiment(self, experiment_id: str) -> Experiment:
        return self._experiment_tracker.get(experiment_id)

    # ── Evaluation ────────────────────────────────────────────────────────────

    async def evaluate(
        self,
        model_id:      str,
        model_version: str,
        dataset:       Any,
        model:         Any,
        task:          ModelTask,
        **kwargs: Any,
    ) -> EvaluationReport:
        self._require_running()
        t0 = time.time()
        report = await self._eval_engine.evaluate(model, dataset, task, **kwargs)
        self._perf_monitor.record_eval(time.time() - t0)
        return report

    # ── Deployment ────────────────────────────────────────────────────────────

    def deploy_model(
        self,
        model_id:      str,
        model_version: str,
        strategy:      DeploymentStrategy = DeploymentStrategy.DIRECT,
        *,
        metrics:       Optional[dict] = None,
        notes:         str            = "",
    ) -> DeploymentRecord:
        self._require_running()
        record = self._deployment_engine.deploy(
            model_id, model_version, strategy, metrics=metrics, notes=notes
        )
        self._perf_monitor.record_deploy()
        try:
            meta = self._model_registry.get(model_id)
            meta.mark_deployed()
        except ModelNotFoundError:
            pass
        self._history.append(
            LearningHistoryEntry.create("deployment", record.deployment_id, "deployed",
                                        {"model_id": model_id, "version": model_version})
        )
        return record

    def rollback_model(self, model_id: str, reason: str = "") -> Optional[DeploymentRecord]:
        self._require_running()
        rec = self._deployment_engine.rollback(model_id, reason)
        if rec is not None:
            self._perf_monitor.record_rollback()
        return rec

    # ── Accessors for subsystems ──────────────────────────────────────────────

    @property
    def feature_engine(self) -> FeatureEngine:
        return self._feature_engine

    @property
    def drift_detector(self) -> DriftDetector:
        return self._drift_detector

    @property
    def model_monitor(self) -> ModelMonitor:
        return self._model_monitor

    @property
    def alert_manager(self) -> AlertManager:
        return self._alert_manager

    @property
    def data_monitor(self) -> DataMonitor:
        return self._data_monitor

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        return self._checkpoint_mgr

    @property
    def hyperparameter_manager(self) -> HyperparameterManager:
        return HyperparameterManager()

    @property
    def history(self) -> LearningHistory:
        return self._history

    # ── Aggregated stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "status":          self.status().value,
            "uptime_sec":      self.uptime_sec(),
            "jobs":            self._job_registry.stats(),
            "models":          self._model_registry.stats(),
            "datasets":        self._dataset_registry.stats(),
            "experiments":     self._experiment_tracker.stats(),
            "deployments":     self._deployment_engine.stats(),
            "performance":     self._perf_monitor.stats(),
            "alerts":          self._alert_manager.stats(),
            "history_entries": self._history.count(),
        }


# ── Singleton management ──────────────────────────────────────────────────────

_instance: Optional[LearningEngine] = None
_lock      = threading.Lock()


def get_learning_engine(auto_start: bool = False) -> LearningEngine:
    """
    Return the module-level LearningEngine singleton.

    If ``auto_start=True`` and the engine is not yet running, it is started
    synchronously using ``asyncio.run()``.  Only use ``auto_start`` in test
    or script contexts — production callers should call ``await engine.start()``
    explicitly.
    """
    global _instance
    with _lock:
        if _instance is None:
            _instance = LearningEngine()
    if auto_start and not _instance.is_running():
        asyncio.run(_instance.start())
    return _instance


def reset_learning_engine() -> None:
    """Destroy the singleton (for testing)."""
    global _instance
    with _lock:
        _instance = None
