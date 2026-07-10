"""iios/integration/history/core/historical_dataset.py

Named, versioned collection of historical records.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import (
    CompressionType,
    DataFormat,
    DatasetStatus,
    HistoricalDataType,
    PartitionStrategy,
)


@dataclass
class HistoricalDataset:
    """
    Metadata descriptor for one historical dataset.

    The dataset acts as the top-level namespace.  Actual records live in
    HistoricalPartition objects that reference this dataset_id.

    Datasets are designed to hold decades of data at arbitrary granularity
    for any HistoricalDataType.
    """

    dataset_id:          str                = field(default_factory=lambda: str(uuid.uuid4()))
    name:                str                = ""
    description:         str                = ""
    data_type:           HistoricalDataType = HistoricalDataType.CUSTOM
    symbols:             list[str]          = field(default_factory=list)
    schema:              dict[str, str]     = field(default_factory=dict)   # field → dtype

    # Time bounds
    start_ts:            float              = 0.0
    end_ts:              float              = 0.0

    # Storage
    format:              DataFormat         = DataFormat.RAW
    compression:         CompressionType    = CompressionType.NONE
    partition_strategy:  PartitionStrategy  = PartitionStrategy.BY_DATE
    partition_size:      int                = 100_000       # records per partition

    # Retention
    retention_days:      int                = 3_650         # 10 years

    # Counters
    record_count:        int                = 0
    partition_count:     int                = 0
    size_bytes:          int                = 0

    # Lifecycle
    version:             int                = 1
    status:              DatasetStatus      = DatasetStatus.ACTIVE
    is_sealed:           bool               = False
    tags:                list[str]          = field(default_factory=list)
    source:              str                = ""     # provider / system that owns this dataset
    owner:               str                = ""

    created_at:          float              = field(default_factory=time.time)
    updated_at:          float              = field(default_factory=time.time)
    metadata:            dict[str, Any]     = field(default_factory=dict)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def touch(self, record_count_delta: int = 0) -> None:
        self.updated_at   = time.time()
        self.record_count += record_count_delta

    def span_days(self) -> float:
        if self.start_ts == 0.0 or self.end_ts == 0.0:
            return 0.0
        return (self.end_ts - self.start_ts) / 86_400

    def is_expired(self) -> bool:
        if self.retention_days <= 0:
            return False
        return (time.time() - self.created_at) / 86_400 > self.retention_days

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id":         self.dataset_id,
            "name":               self.name,
            "data_type":          self.data_type.value,
            "symbols":            self.symbols,
            "start_ts":           self.start_ts,
            "end_ts":             self.end_ts,
            "record_count":       self.record_count,
            "partition_count":    self.partition_count,
            "size_bytes":         self.size_bytes,
            "version":            self.version,
            "status":             self.status.value,
            "created_at":         self.created_at,
            "updated_at":         self.updated_at,
        }
