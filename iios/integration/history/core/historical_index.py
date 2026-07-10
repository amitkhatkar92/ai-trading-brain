"""iios/integration/history/core/historical_index.py

Index entries for O(log n) dataset lookup.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import HistoricalDataType


@dataclass
class HistoricalIndexEntry:
    """
    One entry in the dataset index.

    The index maps (dataset_id, symbol, time_range) → partition_id, enabling
    the query engine to skip irrelevant partitions entirely during range scans.
    """

    index_id:      str                = field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id:    str                = ""
    partition_id:  str                = ""
    data_type:     HistoricalDataType = HistoricalDataType.CUSTOM
    symbol:        str                = ""
    start_ts:      float              = 0.0
    end_ts:        float              = 0.0
    record_count:  int                = 0
    offset_bytes:  int                = 0   # byte offset within partition file
    created_at:    float              = field(default_factory=time.time)

    def contains_ts(self, ts: float) -> bool:
        return self.start_ts <= ts <= self.end_ts

    def overlaps(self, start: float, end: float) -> bool:
        return self.start_ts <= end and self.end_ts >= start

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_id":     self.index_id,
            "dataset_id":   self.dataset_id,
            "partition_id": self.partition_id,
            "symbol":       self.symbol,
            "start_ts":     self.start_ts,
            "end_ts":       self.end_ts,
            "record_count": self.record_count,
        }


class HistoricalIndex:
    """
    In-memory sorted index for one dataset.

    Entries are sorted by start_ts for binary-search range lookup.
    """

    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        self._entries:  list[HistoricalIndexEntry] = []
        self._dirty     = False

    def add(self, entry: HistoricalIndexEntry) -> None:
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.start_ts)
        self._dirty = True

    def remove(self, partition_id: str) -> None:
        self._entries = [e for e in self._entries if e.partition_id != partition_id]

    def find_range(
        self,
        start_ts: float,
        end_ts:   float,
        symbol:   str = "",
    ) -> list[HistoricalIndexEntry]:
        """Return all index entries that overlap the requested time range."""
        results = [
            e for e in self._entries
            if e.overlaps(start_ts, end_ts) and (not symbol or e.symbol == symbol or e.symbol == "")
        ]
        return results

    def find_for_ts(self, ts: float, symbol: str = "") -> list[HistoricalIndexEntry]:
        return self.find_range(ts, ts, symbol)

    def count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self._dirty = True
