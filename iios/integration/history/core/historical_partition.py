"""iios/integration/history/core/historical_partition.py

One shard/chunk of a dataset — the unit of storage and compression.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import (
    CompressionType,
    DatasetStatus,
    HistoricalDataType,
    PartitionStrategy,
)
from iios.integration.history.core.historical_record import HistoricalRecord


@dataclass
class HistoricalPartition:
    """
    Stores a contiguous slice of a dataset's records.

    Partitions are the physical storage granularity: datasets are split into
    partitions for efficient I/O, compression, and parallel access.
    """

    partition_id:       str                = field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id:         str                = ""
    data_type:          HistoricalDataType = HistoricalDataType.CUSTOM
    partition_key:      str                = ""   # e.g. "2024-01" or "AAPL" or "0001"
    strategy:           PartitionStrategy  = PartitionStrategy.BY_DATE
    start_ts:           float              = 0.0
    end_ts:             float              = 0.0
    record_count:       int                = 0
    size_bytes:         int                = 0
    compression:        CompressionType    = CompressionType.NONE
    checksum:           str                = ""
    status:             DatasetStatus      = DatasetStatus.ACTIVE
    is_sealed:          bool               = False  # sealed = no more appends
    records:            list[HistoricalRecord] = field(default_factory=list)
    created_at:         float              = field(default_factory=time.time)
    updated_at:         float              = field(default_factory=time.time)
    metadata:           dict[str, Any]     = field(default_factory=dict)

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def append(self, record: HistoricalRecord) -> None:
        """Append a record to this partition. Updates bounds & counters."""
        if self.is_sealed:
            raise RuntimeError(f"Partition {self.partition_id} is sealed.")
        record.partition_id = self.partition_id
        self.records.append(record)
        self.record_count = len(self.records)
        self.updated_at   = time.time()
        if self.start_ts == 0.0 or record.timestamp < self.start_ts:
            self.start_ts = record.timestamp
        if record.timestamp > self.end_ts:
            self.end_ts = record.timestamp

    def seal(self) -> None:
        """Mark partition as sealed (immutable)."""
        self.is_sealed = True
        self.updated_at = time.time()

    def span_sec(self) -> float:
        return max(0.0, self.end_ts - self.start_ts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition_id":  self.partition_id,
            "dataset_id":    self.dataset_id,
            "partition_key": self.partition_key,
            "strategy":      self.strategy.value,
            "start_ts":      self.start_ts,
            "end_ts":        self.end_ts,
            "record_count":  self.record_count,
            "size_bytes":    self.size_bytes,
            "compression":   self.compression.value,
            "is_sealed":     self.is_sealed,
            "created_at":    self.created_at,
        }
