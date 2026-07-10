"""iios/integration/history/core/historical_snapshot.py

Point-in-time snapshot of dataset state.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import HistoricalDataType


@dataclass
class HistoricalSnapshot:
    """
    Captures the state of a dataset at one moment in time.

    Snapshots serve as recovery anchors and support fast seek operations:
    instead of replaying from the beginning, a replay engine can load the
    nearest snapshot and replay only the delta.
    """

    snapshot_id:  str                = field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id:   str                = ""
    data_type:    HistoricalDataType = HistoricalDataType.CUSTOM
    timestamp:    float              = 0.0      # the point in time this snapshot represents
    record_count: int                = 0
    size_bytes:   int                = 0
    checksum:     str                = ""       # SHA-256 of payload
    description:  str                = ""
    is_complete:  bool               = True     # False = partial / in-progress
    created_at:   float              = field(default_factory=time.time)
    metadata:     dict[str, Any]     = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":  self.snapshot_id,
            "dataset_id":   self.dataset_id,
            "data_type":    self.data_type.value,
            "timestamp":    self.timestamp,
            "record_count": self.record_count,
            "size_bytes":   self.size_bytes,
            "checksum":     self.checksum,
            "is_complete":  self.is_complete,
            "created_at":   self.created_at,
        }
