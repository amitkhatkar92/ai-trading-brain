"""iios/integration/history/simulation/dataset_loader.py

Loads datasets for simulation runs from a storage backend.
"""
from __future__ import annotations

import logging
from typing import Any

from iios.integration.history.core.historical_record  import HistoricalRecord
from iios.integration.history.history_constants       import HistoricalDataType
from iios.integration.history.history_exceptions      import DatasetNotFoundError
from iios.integration.history.storage.storage_backend import StorageBackend

logger = logging.getLogger(__name__)


class DatasetLoader:
    """
    Loads sorted HistoricalRecord lists for simulation or replay.

    Delegates all I/O to the configured StorageBackend.
    Supports incremental (lazy) loading via ``load_batch()``.
    """

    def __init__(self, backend: StorageBackend) -> None:
        self._backend = backend
        self._stats: dict[str, int] = {"loads": 0, "records_loaded": 0}

    async def load(
        self,
        dataset_id: str,
        start_ts:   float,
        end_ts:     float,
        symbols:    list[str] | None = None,
        limit:      int              = 0,
    ) -> list[HistoricalRecord]:
        """
        Load all matching records from a single dataset.
        Returns records sorted by timestamp ascending.
        """
        records = []
        if symbols:
            for sym in symbols:
                batch = self._backend.read_range(
                    dataset_id, start_ts, end_ts, symbol=sym, limit=limit
                )
                records.extend(batch)
            records.sort(key=lambda r: r.timestamp)
        else:
            records = self._backend.read_range(
                dataset_id, start_ts, end_ts, limit=limit
            )

        self._stats["loads"]          += 1
        self._stats["records_loaded"] += len(records)
        logger.debug(
            "[DatasetLoader] Loaded %d records from '%s' [%.0f, %.0f].",
            len(records), dataset_id, start_ts, end_ts,
        )
        return records

    async def load_multi(
        self,
        dataset_ids: list[str],
        start_ts:    float,
        end_ts:      float,
        symbols:     list[str] | None = None,
        limit:       int              = 0,
    ) -> list[HistoricalRecord]:
        """
        Load and merge records from multiple datasets, sorted by timestamp.
        """
        all_records: list[HistoricalRecord] = []
        for did in dataset_ids:
            try:
                batch = await self.load(did, start_ts, end_ts, symbols, limit)
                all_records.extend(batch)
            except DatasetNotFoundError:
                logger.warning("[DatasetLoader] Dataset '%s' not found, skipping.", did)

        all_records.sort(key=lambda r: r.timestamp)
        if limit > 0:
            all_records = all_records[:limit]
        return all_records

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
