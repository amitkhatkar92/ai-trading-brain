"""experiments/experiment_tracker.py — Thread-safe experiment store."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    DEFAULT_MAX_EXPERIMENTS,
    ExperimentStatus,
    LearningType,
    ModelTask,
)
from iios.integration.research.learning.learning_exceptions import (
    ExperimentError,
    ExperimentNotFoundError,
)
from iios.integration.research.learning.core.experiment import Experiment


class ExperimentTracker:
    """
    Stores and manages Experiment objects.
    Thread-safe via a single RLock.
    """

    def __init__(self, max_experiments: int = DEFAULT_MAX_EXPERIMENTS) -> None:
        self._store: dict[str, Experiment] = {}
        self._max   = max_experiments
        self._lock  = threading.RLock()
        self._total = 0

    def create_experiment(
        self,
        name:             str,
        model_task:       ModelTask,
        learning_type:    LearningType,
        *,
        description:      Optional[str] = None,
        best_metric_name: str           = "val_loss",
        higher_is_better: bool          = False,
        tags:             Optional[list] = None,
    ) -> Experiment:
        with self._lock:
            if len(self._store) >= self._max:
                raise ExperimentError(f"Experiment capacity ({self._max}) reached")
            exp = Experiment.create(
                name             = name,
                model_task       = model_task,
                learning_type    = learning_type,
                description      = description,
                best_metric_name = best_metric_name,
                higher_is_better = higher_is_better,
                tags             = tags,
            )
            self._store[exp.experiment_id] = exp
            self._total += 1
        return exp

    def get(self, experiment_id: str) -> Experiment:
        with self._lock:
            exp = self._store.get(experiment_id)
        if exp is None:
            raise ExperimentNotFoundError(f"Experiment '{experiment_id}' not found")
        return exp

    def add_job(self, experiment_id: str, job_id: str) -> None:
        exp = self.get(experiment_id)
        with self._lock:
            exp.add_job(job_id)

    def update_best(
        self,
        experiment_id: str,
        job_id:        str,
        metric_value:  float,
    ) -> None:
        exp = self.get(experiment_id)
        with self._lock:
            exp.update_best(job_id, metric_value)

    def complete(self, experiment_id: str) -> None:
        self.get(experiment_id).complete()

    def fail(self, experiment_id: str, message: str = "") -> None:
        self.get(experiment_id).fail(message)

    def all_experiments(self, status: Optional[ExperimentStatus] = None) -> list[Experiment]:
        with self._lock:
            exps = list(self._store.values())
        if status is not None:
            exps = [e for e in exps if e.status == status]
        return exps

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for exp in self._store.values():
                key = exp.status.value
                by_status[key] = by_status.get(key, 0) + 1
            return {
                "total":      len(self._store),
                "registered": self._total,
                "by_status":  by_status,
            }
