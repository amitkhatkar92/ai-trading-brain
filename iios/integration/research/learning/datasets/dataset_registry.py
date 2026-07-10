"""datasets/dataset_registry.py — Thread-safe registry of TrainingDataset objects."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import DEFAULT_MAX_DATASETS
from iios.integration.research.learning.learning_exceptions import (
    DatasetNotFoundError,
    DatasetError,
)
from iios.integration.research.learning.datasets.training_dataset import TrainingDataset
from iios.integration.research.learning.datasets.dataset_version  import DatasetVersion


class DatasetRegistry:
    """
    Central in-memory store for TrainingDataset objects and their version history.
    Thread-safe via a single RLock.
    """

    def __init__(self, max_datasets: int = DEFAULT_MAX_DATASETS) -> None:
        self._datasets:  dict[str, TrainingDataset]      = {}
        self._versions:  dict[str, list[DatasetVersion]] = {}  # dataset_id → versions
        self._max        = max_datasets
        self._lock       = threading.RLock()
        self._total_registered = 0

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, dataset: TrainingDataset, *, change_summary: str = "initial") -> DatasetVersion:
        with self._lock:
            if len(self._datasets) >= self._max:
                raise DatasetError(f"Dataset registry capacity ({self._max}) reached")
            existing = self._datasets.get(dataset.dataset_id)
            parent_version = None
            if existing is not None:
                versions = self._versions.get(dataset.dataset_id, [])
                if versions:
                    parent_version = versions[-1].version
            self._datasets[dataset.dataset_id] = dataset
            version = DatasetVersion.create(
                dataset_id     = dataset.dataset_id,
                version        = dataset.version,
                record_count   = len(dataset),
                change_summary = change_summary,
                parent_version = parent_version,
            )
            if dataset.dataset_id not in self._versions:
                self._versions[dataset.dataset_id] = []
                self._total_registered += 1
            self._versions[dataset.dataset_id].append(version)
        return version

    def get(self, dataset_id: str) -> TrainingDataset:
        with self._lock:
            ds = self._datasets.get(dataset_id)
        if ds is None:
            raise DatasetNotFoundError(f"Dataset {dataset_id!r} not found")
        return ds

    def remove(self, dataset_id: str) -> None:
        with self._lock:
            if dataset_id not in self._datasets:
                raise DatasetNotFoundError(f"Dataset {dataset_id!r} not found")
            del self._datasets[dataset_id]
            self._versions.pop(dataset_id, None)

    def has(self, dataset_id: str) -> bool:
        with self._lock:
            return dataset_id in self._datasets

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_datasets(self) -> list[TrainingDataset]:
        with self._lock:
            return list(self._datasets.values())

    def find_by_name(self, name: str) -> list[TrainingDataset]:
        with self._lock:
            return [d for d in self._datasets.values() if d.name == name]

    def versions(self, dataset_id: str) -> list[DatasetVersion]:
        with self._lock:
            return list(self._versions.get(dataset_id, []))

    def count(self) -> int:
        with self._lock:
            return len(self._datasets)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":            len(self._datasets),
                "total_registered": self._total_registered,
                "capacity":         self._max,
            }
