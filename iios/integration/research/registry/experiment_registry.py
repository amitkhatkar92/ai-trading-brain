"""iios/integration/research/registry/experiment_registry.py

Thread-safe registry for ResearchExperiment objects.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.integration.research.core.research_experiment import ResearchExperiment
from iios.integration.research.research_constants        import (
    DEFAULT_MAX_EXPERIMENTS,
    ExperimentPriority,
    ExperimentStatus,
)
from iios.integration.research.research_exceptions       import (
    ResearchExperimentAlreadyExistsError,
    ResearchExperimentCapacityError,
    ResearchExperimentNotFoundError,
)

logger = logging.getLogger(__name__)


class ExperimentRegistry:
    """
    Central registry for all research experiments.

    Provides O(1) lookup by experiment_id and filtered list queries
    by project, status, or priority.
    """

    def __init__(self, max_experiments: int = DEFAULT_MAX_EXPERIMENTS) -> None:
        self._max   = max_experiments
        self._lock  = threading.RLock()
        self._store: dict[str, ResearchExperiment] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, experiment: ResearchExperiment) -> None:
        with self._lock:
            if experiment.experiment_id in self._store:
                raise ResearchExperimentAlreadyExistsError(
                    f"Experiment '{experiment.experiment_id}' already registered."
                )
            if len(self._store) >= self._max:
                raise ResearchExperimentCapacityError(
                    f"Experiment capacity ({self._max}) reached."
                )
            self._store[experiment.experiment_id] = experiment
            logger.info(
                "[ExperimentRegistry] Registered experiment '%s'.",
                experiment.name or experiment.experiment_id,
            )

    def get(self, experiment_id: str) -> ResearchExperiment:
        with self._lock:
            e = self._store.get(experiment_id)
            if e is None:
                raise ResearchExperimentNotFoundError(
                    f"Experiment '{experiment_id}' not found."
                )
            return e

    def update(self, experiment: ResearchExperiment) -> None:
        with self._lock:
            if experiment.experiment_id not in self._store:
                raise ResearchExperimentNotFoundError(
                    f"Experiment '{experiment.experiment_id}' not found."
                )
            self._store[experiment.experiment_id] = experiment

    def remove(self, experiment_id: str) -> None:
        with self._lock:
            if experiment_id not in self._store:
                raise ResearchExperimentNotFoundError(
                    f"Experiment '{experiment_id}' not found."
                )
            del self._store[experiment_id]

    def has(self, experiment_id: str) -> bool:
        with self._lock:
            return experiment_id in self._store

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_experiments(self) -> list[ResearchExperiment]:
        with self._lock:
            return list(self._store.values())

    def find_by_project(self, project_id: str) -> list[ResearchExperiment]:
        with self._lock:
            return [e for e in self._store.values() if e.project_id == project_id]

    def find_by_status(self, status: ExperimentStatus) -> list[ResearchExperiment]:
        with self._lock:
            return [e for e in self._store.values() if e.status == status]

    def find_by_priority(self, priority: ExperimentPriority) -> list[ResearchExperiment]:
        with self._lock:
            return [e for e in self._store.values() if e.priority == priority]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for e in self._store.values():
                by_status[e.status.value] = by_status.get(e.status.value, 0) + 1
            return {
                "total":    len(self._store),
                "capacity": self._max,
                "by_status": by_status,
            }
