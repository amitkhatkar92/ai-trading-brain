"""iios/integration/history/query/query_engine.py

High-level query facade for the historical data framework.

Uses DatasetSelector → StorageBackend → HistoricalSearch pipeline.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from iios.integration.history.core.historical_record   import HistoricalRecord
from iios.integration.history.history_constants        import (
    DEFAULT_QUERY_TIMEOUT_SEC,
    DEFAULT_MAX_QUERY_RESULTS,
)
from iios.integration.history.history_exceptions       import (
    QueryTimeoutError,
    QueryValidationError,
    QueryResultTooLargeError,
)
from iios.integration.history.query.dataset_selector   import DatasetSelector
from iios.integration.history.query.historical_filter  import HistoricalFilter
from iios.integration.history.query.historical_search  import HistoricalSearch
from iios.integration.history.storage.storage_backend  import StorageBackend

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Unified query interface for historical records.

    Supports:
    - Date range scans
    - Symbol filtering
    - Data type filtering
    - Custom field predicates
    - Pagination
    - Sorted results
    """

    def __init__(
        self,
        backend:  StorageBackend,
        selector: DatasetSelector | None = None,
        search:   HistoricalSearch | None = None,
        timeout_sec: float = DEFAULT_QUERY_TIMEOUT_SEC,
        max_results: int   = DEFAULT_MAX_QUERY_RESULTS,
    ) -> None:
        self._backend     = backend
        self._selector    = selector or DatasetSelector()
        self._search      = search   or HistoricalSearch()
        self._timeout     = timeout_sec
        self._max_results = max_results
        self._stats: dict[str, int] = {
            "queries": 0, "records_returned": 0, "timeouts": 0, "errors": 0,
        }

    async def query(self, f: HistoricalFilter) -> list[HistoricalRecord]:
        """
        Execute a historical query.

        1. Validate filter
        2. Select candidate datasets
        3. Load records from storage
        4. Apply search / filter / sort / page
        5. Return results
        """
        self._validate(f)
        deadline = time.time() + self._timeout
        all_records: list[HistoricalRecord] = []

        # Resolve candidate datasets
        all_datasets = self._backend.list_datasets(
            data_type=f.data_types[0] if len(f.data_types) == 1 else None
        )
        selected = self._selector.select(all_datasets, f)

        for ds in selected:
            if time.time() > deadline:
                self._stats["timeouts"] += 1
                raise QueryTimeoutError(
                    f"Query exceeded {self._timeout}s timeout."
                )
            start_ts = f.start_ts if f.start_ts is not None else ds.start_ts
            end_ts   = f.end_ts   if f.end_ts   is not None else ds.end_ts
            for sym in (f.symbols or [""]):
                batch = self._backend.read_range(
                    ds.dataset_id, start_ts, end_ts, symbol=sym,
                )
                all_records.extend(batch)

        # In-memory filtering + sort + page
        result = self._search.search(all_records, f)

        if len(result) > self._max_results:
            raise QueryResultTooLargeError(
                f"Query returned {len(result)} records; max is {self._max_results}."
            )

        self._stats["queries"]          += 1
        self._stats["records_returned"] += len(result)
        logger.debug(
            "[QueryEngine] Query returned %d records from %d datasets.",
            len(result), len(selected),
        )
        return result

    def _validate(self, f: HistoricalFilter) -> None:
        if f.start_ts is not None and f.end_ts is not None:
            if f.start_ts > f.end_ts:
                raise QueryValidationError("start_ts must be ≤ end_ts.")
        if f.limit < 0:
            raise QueryValidationError("limit must be ≥ 0.")
        if f.page < 0:
            raise QueryValidationError("page must be ≥ 0.")

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
