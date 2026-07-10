"""iios/integration/history/history_manager.py

High-level coordinator for all historical data operations.

Wires registry, storage, indexer, query engine, and cache together
behind a single, simple API surface.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from iios.integration.history.cache                            import HistoryCache
from iios.integration.history.core.historical_dataset         import HistoricalDataset
from iios.integration.history.core.historical_record          import HistoricalRecord
from iios.integration.history.core.historical_snapshot        import HistoricalSnapshot
from iios.integration.history.history_constants               import (
    DatasetStatus,
    HistoricalDataType,
)
from iios.integration.history.history_context                 import HistoryContext
from iios.integration.history.history_exceptions              import DatasetNotFoundError
from iios.integration.history.history_registry                import HistoryRegistry
from iios.integration.history.indexing.dataset_index          import DatasetIndexManager
from iios.integration.history.query.historical_filter         import HistoricalFilter
from iios.integration.history.query.query_engine              import QueryEngine
from iios.integration.history.storage.storage_backend         import StorageBackend

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Unified historical data manager.

    Responsibilities:
    - Dataset lifecycle (create, update, archive, delete)
    - Record ingestion with automatic partition management
    - Query execution with caching
    - Snapshot creation / restoration
    - Background indexing
    """

    def __init__(
        self,
        registry:      HistoryRegistry,
        backend:       StorageBackend,
        index_manager: DatasetIndexManager,
        query_engine:  QueryEngine,
        cache:         HistoryCache,
    ) -> None:
        self._registry  = registry
        self._backend   = backend
        self._index     = index_manager
        self._query     = query_engine
        self._cache     = cache
        self._stats: dict[str, int] = {
            "datasets_created": 0,
            "records_ingested": 0,
            "queries_executed": 0,
            "cache_hits":       0,
            "snapshots_created": 0,
        }

    # ── Dataset management ────────────────────────────────────────────────────

    def create_dataset(self, dataset: HistoricalDataset) -> HistoricalDataset:
        """Register and persist a new dataset."""
        with HistoryContext.scope("create_dataset", dataset_id=dataset.dataset_id):
            self._registry.register(dataset)
            self._backend.create_dataset(dataset)
            self._index.create_index(dataset.dataset_id)
            self._stats["datasets_created"] += 1
            logger.info("[HistoryManager] Created dataset '%s'.", dataset.name)
            return dataset

    def get_dataset(self, dataset_id: str) -> HistoricalDataset:
        return self._registry.get(dataset_id)

    def list_datasets(
        self,
        data_type: HistoricalDataType | None = None,
    ) -> list[HistoricalDataset]:
        return self._backend.list_datasets(data_type=data_type)

    def archive_dataset(self, dataset_id: str) -> None:
        ds = self._registry.get(dataset_id)
        ds.status = DatasetStatus.ARCHIVED
        self._backend.update_dataset(ds)
        self._registry.update(ds)

    def delete_dataset(self, dataset_id: str) -> None:
        self._registry.unregister(dataset_id)
        self._backend.delete_dataset(dataset_id)
        self._index.drop_index(dataset_id)

    # ── Record ingestion ──────────────────────────────────────────────────────

    def ingest(self, dataset_id: str, record: HistoricalRecord) -> None:
        """Append one record to an existing dataset."""
        with HistoryContext.scope("ingest", dataset_id=dataset_id):
            self._backend.append_record(dataset_id, record)
            self._stats["records_ingested"] += 1

    def ingest_batch(
        self,
        dataset_id: str,
        records:    list[HistoricalRecord],
    ) -> int:
        """Batch ingest. Returns count ingested."""
        with HistoryContext.scope("ingest_batch", dataset_id=dataset_id):
            count = 0
            for r in records:
                self._backend.append_record(dataset_id, r)
                count += 1
            self._stats["records_ingested"] += count
            logger.debug(
                "[HistoryManager] Ingested %d records into '%s'.", count, dataset_id
            )
            return count

    # ── Query ─────────────────────────────────────────────────────────────────

    async def query(
        self,
        f:         HistoricalFilter,
        use_cache: bool = True,
    ) -> list[HistoricalRecord]:
        """Execute a historical query with optional result caching."""
        cache_key = self._cache_key(f)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return cached

        with HistoryContext.scope("query"):
            result = await self._query.query(f)

        if use_cache and result:
            self._cache.set(cache_key, result)

        self._stats["queries_executed"] += 1
        return result

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def create_snapshot(self, dataset_id: str) -> HistoricalSnapshot:
        """Create a point-in-time snapshot of a dataset."""
        ds = self._registry.get(dataset_id)
        snap = HistoricalSnapshot(
            dataset_id   = dataset_id,
            data_type    = ds.data_type,
            timestamp    = time.time(),
            record_count = ds.record_count,
            size_bytes   = ds.size_bytes,
            description  = f"Auto-snapshot of {ds.name}",
        )
        self._backend.save_snapshot(snap)
        self._stats["snapshots_created"] += 1
        return snap

    def list_snapshots(self, dataset_id: str) -> list[HistoricalSnapshot]:
        return self._backend.list_snapshots(dataset_id)

    # ── Index ─────────────────────────────────────────────────────────────────

    def reindex_dataset(self, dataset_id: str) -> None:
        """Rebuild the index for a dataset from its stored partitions."""
        self._index.drop_index(dataset_id)
        self._index.create_index(dataset_id)
        for p in self._backend.list_partitions(dataset_id):
            self._index.index_partition(p)
        logger.info("[HistoryManager] Reindexed dataset '%s'.", dataset_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(f: HistoricalFilter) -> str:
        return (
            f"q:{','.join(sorted(f.dataset_ids))}"
            f":{f.start_ts}:{f.end_ts}"
            f":{','.join(sorted(f.symbols))}"
            f":{f.limit}:{f.page}"
        )

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "registry":  self._registry.stats(),
            "cache":     self._cache.stats(),
            "index":     self._index.stats(),
            "query":     self._query.stats(),
        }
