"""iios/integration/history/history_registry.py

Thread-safe registry that maps dataset_id → HistoricalDataset.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.integration.history.core.historical_dataset import HistoricalDataset
from iios.integration.history.history_constants import (
    DEFAULT_MAX_DATASETS,
    DatasetStatus,
    HistoricalDataType,
)
from iios.integration.history.history_exceptions import (
    DatasetAlreadyExistsError,
    DatasetNotFoundError,
    HistoryRegistryFullError,
)

logger = logging.getLogger(__name__)


class HistoryRegistry:
    """
    In-memory registry of HistoricalDataset descriptors.

    Provides O(1) lookup by dataset_id and filtered lists by type / symbol.
    """

    def __init__(self, max_datasets: int = DEFAULT_MAX_DATASETS) -> None:
        self._max   = max_datasets
        self._lock  = threading.RLock()
        self._store: dict[str, HistoricalDataset] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, dataset: HistoricalDataset) -> None:
        with self._lock:
            if dataset.dataset_id in self._store:
                raise DatasetAlreadyExistsError(
                    f"Dataset '{dataset.dataset_id}' already registered."
                )
            if len(self._store) >= self._max:
                raise HistoryRegistryFullError(
                    f"Registry full ({self._max} datasets)."
                )
            self._store[dataset.dataset_id] = dataset
            logger.info("[HistoryRegistry] Registered dataset '%s' (%s).",
                        dataset.name, dataset.data_type.value)

    def unregister(self, dataset_id: str) -> None:
        with self._lock:
            if dataset_id not in self._store:
                raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            del self._store[dataset_id]

    def get(self, dataset_id: str) -> HistoricalDataset:
        with self._lock:
            ds = self._store.get(dataset_id)
            if ds is None:
                raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            return ds

    def has(self, dataset_id: str) -> bool:
        with self._lock:
            return dataset_id in self._store

    def update(self, dataset: HistoricalDataset) -> None:
        with self._lock:
            if dataset.dataset_id not in self._store:
                raise DatasetNotFoundError(f"Dataset '{dataset.dataset_id}' not found.")
            self._store[dataset.dataset_id] = dataset

    # ── Discovery ─────────────────────────────────────────────────────────────

    def all_datasets(self) -> list[HistoricalDataset]:
        with self._lock:
            return list(self._store.values())

    def find_by_type(self, data_type: HistoricalDataType) -> list[HistoricalDataset]:
        with self._lock:
            return [d for d in self._store.values() if d.data_type == data_type]

    def find_by_symbol(self, symbol: str) -> list[HistoricalDataset]:
        with self._lock:
            return [
                d for d in self._store.values()
                if not d.symbols or symbol in d.symbols
            ]

    def find_active(self) -> list[HistoricalDataset]:
        with self._lock:
            return [d for d in self._store.values() if d.status == DatasetStatus.ACTIVE]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":    len(self._store),
                "capacity": self._max,
                "active":   sum(1 for d in self._store.values() if d.status == DatasetStatus.ACTIVE),
            }
