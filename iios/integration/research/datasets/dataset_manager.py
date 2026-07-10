"""iios/integration/research/datasets/dataset_manager.py

Manages research dataset lifecycle: registration, versioning, lineage, snapshots.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.integration.research.core.research_dataset   import ResearchDataset, DatasetSnapshot
from iios.integration.research.research_constants       import (
    DEFAULT_MAX_DATASETS,
    ResearchDatasetStatus,
)
from iios.integration.research.research_exceptions      import (
    ResearchDatasetAlreadyExistsError,
    ResearchDatasetCapacityError,
    ResearchDatasetNotFoundError,
    DatasetLineageError,
)

logger = logging.getLogger(__name__)


class DatasetManager:
    """
    Thread-safe registry and lifecycle manager for research datasets.

    Supports:
    - Dataset registration with deduplication
    - Version management (bump_version)
    - Lineage tracking (parent_ids chain)
    - Snapshot creation
    - Dataset deprecation and archival
    """

    def __init__(self, max_datasets: int = DEFAULT_MAX_DATASETS) -> None:
        self._max   = max_datasets
        self._lock  = threading.RLock()
        self._store: dict[str, ResearchDataset] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, dataset: ResearchDataset) -> ResearchDataset:
        with self._lock:
            if dataset.dataset_id in self._store:
                raise ResearchDatasetAlreadyExistsError(
                    f"Dataset '{dataset.dataset_id}' already registered."
                )
            if len(self._store) >= self._max:
                raise ResearchDatasetCapacityError(
                    f"Dataset capacity ({self._max}) reached."
                )
            self._store[dataset.dataset_id] = dataset
            logger.info("[DatasetManager] Registered dataset '%s' (v%s).",
                        dataset.name, dataset.version)
            return dataset

    def get(self, dataset_id: str) -> ResearchDataset:
        with self._lock:
            ds = self._store.get(dataset_id)
            if ds is None:
                raise ResearchDatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            return ds

    def update(self, dataset: ResearchDataset) -> ResearchDataset:
        with self._lock:
            if dataset.dataset_id not in self._store:
                raise ResearchDatasetNotFoundError(f"Dataset '{dataset.dataset_id}' not found.")
            dataset.touch()
            self._store[dataset.dataset_id] = dataset
            return dataset

    def remove(self, dataset_id: str) -> None:
        with self._lock:
            if dataset_id not in self._store:
                raise ResearchDatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            del self._store[dataset_id]

    def has(self, dataset_id: str) -> bool:
        with self._lock:
            return dataset_id in self._store

    # ── Versioning ────────────────────────────────────────────────────────────

    def new_version(
        self,
        source_dataset_id: str,
        changes:           str = "",
    ) -> ResearchDataset:
        """
        Derive a new dataset version from an existing one.

        The new dataset shares the same name but gets a fresh dataset_id,
        bumped version string, and records the source as a parent.
        """
        src = self.get(source_dataset_id)
        parts   = src.version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new_version = ".".join(parts)

        derived = ResearchDataset(
            name        = src.name,
            description = changes or f"Derived from v{src.version}",
            source_type = src.source_type,
            status      = ResearchDatasetStatus.PENDING,
            version     = new_version,
            schema      = dict(src.schema),
            parent_ids  = list(src.parent_ids) + [source_dataset_id],
            source_ref  = src.source_ref,
            tags        = list(src.tags),
        )
        return self.register(derived)

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def snapshot(self, dataset_id: str, description: str = "") -> DatasetSnapshot:
        ds   = self.get(dataset_id)
        snap = ds.create_snapshot(description=description)
        self.update(ds)
        logger.info("[DatasetManager] Snapshot '%s' created for dataset '%s'.",
                    snap.snapshot_id, dataset_id)
        return snap

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def validate(self, dataset_id: str) -> ResearchDataset:
        ds        = self.get(dataset_id)
        ds.status = ResearchDatasetStatus.VALIDATED
        return self.update(ds)

    def activate(self, dataset_id: str) -> ResearchDataset:
        ds        = self.get(dataset_id)
        ds.status = ResearchDatasetStatus.ACTIVE
        return self.update(ds)

    def deprecate(self, dataset_id: str) -> ResearchDataset:
        ds        = self.get(dataset_id)
        ds.status = ResearchDatasetStatus.DEPRECATED
        return self.update(ds)

    # ── Lineage ───────────────────────────────────────────────────────────────

    def lineage(self, dataset_id: str) -> list[ResearchDataset]:
        """
        Return the full ancestor chain for a dataset, ordered oldest → newest.
        Raises DatasetLineageError if a parent is not found (broken lineage).
        """
        ds       = self.get(dataset_id)
        chain    = []
        for pid in ds.parent_ids:
            try:
                chain.append(self.get(pid))
            except ResearchDatasetNotFoundError as exc:
                raise DatasetLineageError(
                    f"Broken lineage: parent '{pid}' not found for dataset '{dataset_id}'."
                ) from exc
        return chain

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_datasets(self) -> list[ResearchDataset]:
        with self._lock:
            return list(self._store.values())

    def find_by_name(self, name: str) -> list[ResearchDataset]:
        with self._lock:
            return [d for d in self._store.values() if d.name == name]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":    len(self._store),
                "capacity": self._max,
                "active":   sum(1 for d in self._store.values()
                                if d.status == ResearchDatasetStatus.ACTIVE),
            }
