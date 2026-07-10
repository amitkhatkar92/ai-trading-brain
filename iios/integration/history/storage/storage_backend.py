"""iios/integration/history/storage/storage_backend.py

Abstract storage backend + in-memory reference implementation.

Future backends (SQLite, PostgreSQL, S3, Parquet, TimescaleDB) implement
StorageBackend without touching the framework.
"""
from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from iios.integration.history.core.historical_dataset   import HistoricalDataset
from iios.integration.history.core.historical_partition import HistoricalPartition
from iios.integration.history.core.historical_record    import HistoricalRecord
from iios.integration.history.core.historical_snapshot  import HistoricalSnapshot
from iios.integration.history.history_constants import (
    DatasetStatus,
    HistoricalDataType,
    StorageStatus,
)
from iios.integration.history.history_exceptions import (
    DatasetAlreadyExistsError,
    DatasetNotFoundError,
    PartitionNotFoundError,
    StorageCapacityError,
)

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    # ── Dataset CRUD ──────────────────────────────────────────────────────────

    @abstractmethod
    def create_dataset(self, dataset: HistoricalDataset) -> None: ...
    @abstractmethod
    def get_dataset(self, dataset_id: str) -> HistoricalDataset: ...
    @abstractmethod
    def update_dataset(self, dataset: HistoricalDataset) -> None: ...
    @abstractmethod
    def delete_dataset(self, dataset_id: str) -> None: ...
    @abstractmethod
    def list_datasets(self, data_type: HistoricalDataType | None = None) -> list[HistoricalDataset]: ...

    # ── Partition CRUD ────────────────────────────────────────────────────────

    @abstractmethod
    def write_partition(self, partition: HistoricalPartition) -> None: ...
    @abstractmethod
    def read_partition(self, partition_id: str) -> HistoricalPartition: ...
    @abstractmethod
    def delete_partition(self, partition_id: str) -> None: ...
    @abstractmethod
    def list_partitions(self, dataset_id: str) -> list[HistoricalPartition]: ...

    # ── Record access ─────────────────────────────────────────────────────────

    @abstractmethod
    def append_record(self, dataset_id: str, record: HistoricalRecord) -> None: ...
    @abstractmethod
    def read_range(
        self,
        dataset_id: str,
        start_ts: float,
        end_ts:   float,
        symbol:   str = "",
        limit:    int = 0,
    ) -> list[HistoricalRecord]: ...

    # ── Snapshots ─────────────────────────────────────────────────────────────

    @abstractmethod
    def save_snapshot(self, snapshot: HistoricalSnapshot) -> None: ...
    @abstractmethod
    def load_snapshot(self, snapshot_id: str) -> HistoricalSnapshot: ...
    @abstractmethod
    def list_snapshots(self, dataset_id: str) -> list[HistoricalSnapshot]: ...

    # ── Health ────────────────────────────────────────────────────────────────

    @abstractmethod
    def status(self) -> StorageStatus: ...
    @abstractmethod
    def stats(self) -> dict[str, Any]: ...


# ── In-Memory Reference Implementation ────────────────────────────────────────

class InMemoryStorageBackend(StorageBackend):
    """
    Fully in-memory storage backend.

    Suitable for unit tests and ephemeral simulations.
    All data is lost when the process exits.
    """

    def __init__(self, max_records: int = 10_000_000) -> None:
        self._max_records = max_records
        self._lock        = threading.RLock()
        self._datasets:   dict[str, HistoricalDataset]      = {}
        self._partitions: dict[str, HistoricalPartition]    = {}
        self._snapshots:  dict[str, HistoricalSnapshot]     = {}
        # dataset_id → sorted list of records
        self._records:    dict[str, list[HistoricalRecord]] = {}
        self._total_records = 0
        self._stats: dict[str, int] = {
            "datasets_created": 0,
            "partitions_written": 0,
            "records_appended": 0,
            "reads": 0,
        }

    # ── Dataset CRUD ──────────────────────────────────────────────────────────

    def create_dataset(self, dataset: HistoricalDataset) -> None:
        with self._lock:
            if dataset.dataset_id in self._datasets:
                raise DatasetAlreadyExistsError(f"Dataset '{dataset.dataset_id}' already exists.")
            self._datasets[dataset.dataset_id] = dataset
            self._records[dataset.dataset_id]  = []
            self._stats["datasets_created"] += 1

    def get_dataset(self, dataset_id: str) -> HistoricalDataset:
        with self._lock:
            ds = self._datasets.get(dataset_id)
            if ds is None:
                raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            return ds

    def update_dataset(self, dataset: HistoricalDataset) -> None:
        with self._lock:
            if dataset.dataset_id not in self._datasets:
                raise DatasetNotFoundError(f"Dataset '{dataset.dataset_id}' not found.")
            self._datasets[dataset.dataset_id] = dataset

    def delete_dataset(self, dataset_id: str) -> None:
        with self._lock:
            if dataset_id not in self._datasets:
                raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            del self._datasets[dataset_id]
            self._records.pop(dataset_id, None)
            # Remove associated partitions
            to_del = [pid for pid, p in self._partitions.items() if p.dataset_id == dataset_id]
            for pid in to_del:
                del self._partitions[pid]

    def list_datasets(self, data_type: HistoricalDataType | None = None) -> list[HistoricalDataset]:
        with self._lock:
            ds_list = list(self._datasets.values())
            if data_type:
                ds_list = [d for d in ds_list if d.data_type == data_type]
            return ds_list

    # ── Partition CRUD ────────────────────────────────────────────────────────

    def write_partition(self, partition: HistoricalPartition) -> None:
        with self._lock:
            self._partitions[partition.partition_id] = partition
            self._stats["partitions_written"] += 1

    def read_partition(self, partition_id: str) -> HistoricalPartition:
        with self._lock:
            p = self._partitions.get(partition_id)
            if p is None:
                raise PartitionNotFoundError(f"Partition '{partition_id}' not found.")
            return p

    def delete_partition(self, partition_id: str) -> None:
        with self._lock:
            if partition_id not in self._partitions:
                raise PartitionNotFoundError(f"Partition '{partition_id}' not found.")
            del self._partitions[partition_id]

    def list_partitions(self, dataset_id: str) -> list[HistoricalPartition]:
        with self._lock:
            return [p for p in self._partitions.values() if p.dataset_id == dataset_id]

    # ── Record access ─────────────────────────────────────────────────────────

    def append_record(self, dataset_id: str, record: HistoricalRecord) -> None:
        with self._lock:
            if dataset_id not in self._datasets:
                raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found.")
            if self._total_records >= self._max_records:
                raise StorageCapacityError("In-memory storage capacity exceeded.")
            record.dataset_id = dataset_id
            records = self._records[dataset_id]
            # Keep sorted by timestamp via insertion sort (most appends are in order)
            if records and records[-1].timestamp <= record.timestamp:
                records.append(record)
            else:
                from bisect import insort_right
                # Use a key-based approach
                pos = 0
                for i, r in enumerate(records):
                    if r.timestamp <= record.timestamp:
                        pos = i + 1
                records.insert(pos, record)
            self._total_records += 1
            ds = self._datasets[dataset_id]
            ds.record_count += 1
            ds.updated_at    = time.time()
            if ds.start_ts == 0.0 or record.timestamp < ds.start_ts:
                ds.start_ts = record.timestamp
            if record.timestamp > ds.end_ts:
                ds.end_ts = record.timestamp
            self._stats["records_appended"] += 1

    def read_range(
        self,
        dataset_id: str,
        start_ts:   float,
        end_ts:     float,
        symbol:     str = "",
        limit:      int = 0,
    ) -> list[HistoricalRecord]:
        with self._lock:
            records = self._records.get(dataset_id, [])
            result  = [
                r for r in records
                if r.timestamp >= start_ts
                and r.timestamp <= end_ts
                and (not symbol or r.symbol == symbol)
            ]
            self._stats["reads"] += 1
            if limit > 0:
                result = result[:limit]
            return result

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def save_snapshot(self, snapshot: HistoricalSnapshot) -> None:
        with self._lock:
            self._snapshots[snapshot.snapshot_id] = snapshot

    def load_snapshot(self, snapshot_id: str) -> HistoricalSnapshot:
        with self._lock:
            s = self._snapshots.get(snapshot_id)
            if s is None:
                raise StorageNotFoundError(f"Snapshot '{snapshot_id}' not found.")
            return s

    def list_snapshots(self, dataset_id: str) -> list[HistoricalSnapshot]:
        with self._lock:
            return [s for s in self._snapshots.values() if s.dataset_id == dataset_id]

    # ── Health ────────────────────────────────────────────────────────────────

    def status(self) -> StorageStatus:
        return StorageStatus.AVAILABLE

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                **self._stats,
                "total_records":   self._total_records,
                "datasets":        len(self._datasets),
                "partitions":      len(self._partitions),
                "snapshots":       len(self._snapshots),
            }


from iios.integration.history.history_constants import StorageStatus
from iios.integration.history.history_exceptions import StorageNotFoundError
