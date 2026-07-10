"""iios/integration/history/indexing/dataset_index.py

Manages per-dataset HistoricalIndex objects.

Maintains sorted index entries so the query engine can scan only relevant
partitions for any (dataset, symbol, time_range) combination.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.integration.history.core.historical_index     import HistoricalIndex, HistoricalIndexEntry
from iios.integration.history.core.historical_partition import HistoricalPartition
from iios.integration.history.history_constants import HistoricalDataType

logger = logging.getLogger(__name__)


class DatasetIndexManager:
    """
    In-process index manager.

    One HistoricalIndex per dataset.  Background indexing of new partitions
    is supported via ``index_partition()``.
    """

    def __init__(self) -> None:
        self._lock:    threading.RLock = threading.RLock()
        self._indexes: dict[str, HistoricalIndex] = {}
        self._stats: dict[str, int] = {
            "datasets_indexed": 0,
            "partitions_indexed": 0,
            "lookups": 0,
        }

    # ── Index lifecycle ───────────────────────────────────────────────────────

    def create_index(self, dataset_id: str) -> HistoricalIndex:
        with self._lock:
            if dataset_id not in self._indexes:
                self._indexes[dataset_id] = HistoricalIndex(dataset_id)
                self._stats["datasets_indexed"] += 1
            return self._indexes[dataset_id]

    def get_index(self, dataset_id: str) -> HistoricalIndex | None:
        with self._lock:
            return self._indexes.get(dataset_id)

    def drop_index(self, dataset_id: str) -> None:
        with self._lock:
            self._indexes.pop(dataset_id, None)

    # ── Partition indexing ────────────────────────────────────────────────────

    def index_partition(self, partition: HistoricalPartition) -> None:
        """
        Build or update index entries for a partition.

        Creates one index entry per distinct symbol found in the partition.
        If the partition spans many symbols, each gets its own entry for
        efficient per-symbol range scans.
        """
        with self._lock:
            index = self._indexes.get(partition.dataset_id)
            if index is None:
                index = HistoricalIndex(partition.dataset_id)
                self._indexes[partition.dataset_id] = index

        # Gather per-symbol bounds
        symbol_bounds: dict[str, list[float]] = {}
        for r in partition.records:
            sym = r.symbol or ""
            if sym not in symbol_bounds:
                symbol_bounds[sym] = [r.timestamp, r.timestamp]
            else:
                if r.timestamp < symbol_bounds[sym][0]:
                    symbol_bounds[sym][0] = r.timestamp
                if r.timestamp > symbol_bounds[sym][1]:
                    symbol_bounds[sym][1] = r.timestamp

        if not symbol_bounds:
            # No records — create one generic entry covering the partition span
            symbol_bounds[""] = [partition.start_ts, partition.end_ts]

        with self._lock:
            for sym, (s_ts, e_ts) in symbol_bounds.items():
                entry = HistoricalIndexEntry(
                    dataset_id   = partition.dataset_id,
                    partition_id = partition.partition_id,
                    data_type    = partition.data_type,
                    symbol       = sym,
                    start_ts     = s_ts,
                    end_ts       = e_ts,
                    record_count = len([r for r in partition.records if (r.symbol or "") == sym]),
                )
                index.add(entry)
            self._stats["partitions_indexed"] += 1
            logger.debug(
                "[DatasetIndexManager] Indexed partition '%s' (%d symbols).",
                partition.partition_id, len(symbol_bounds),
            )

    # ── Query ─────────────────────────────────────────────────────────────────

    def find_partitions(
        self,
        dataset_id: str,
        start_ts:   float,
        end_ts:     float,
        symbol:     str = "",
    ) -> list[str]:
        """Return partition IDs that overlap the requested range."""
        with self._lock:
            index = self._indexes.get(dataset_id)
            self._stats["lookups"] += 1
            if index is None:
                return []
            entries = index.find_range(start_ts, end_ts, symbol)
            seen: set[str] = set()
            result: list[str] = []
            for e in entries:
                if e.partition_id not in seen:
                    seen.add(e.partition_id)
                    result.append(e.partition_id)
            return result

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
