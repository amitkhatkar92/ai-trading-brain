"""iios/integration/history/query/historical_search.py

Full-scan search over HistoricalRecord payloads.

This is a brute-force search intended for small datasets or tests.
The QueryEngine uses index-accelerated lookup for production volume.
"""
from __future__ import annotations

import logging
from typing import Any

from iios.integration.history.core.historical_record   import HistoricalRecord
from iios.integration.history.history_constants        import SortOrder
from iios.integration.history.query.historical_filter  import HistoricalFilter

logger = logging.getLogger(__name__)


class HistoricalSearch:
    """
    Applies a HistoricalFilter to a list of records (in-memory scan).
    """

    def search(
        self,
        records: list[HistoricalRecord],
        f:       HistoricalFilter,
    ) -> list[HistoricalRecord]:
        """
        Filter, sort and page a list of records.
        Returns a new list; does not modify input.
        """
        result = [r for r in records if f.matches_record(r)]

        # Sort
        key_fn = self._sort_key(f.sort_by)
        result.sort(key=key_fn, reverse=(f.sort_order == SortOrder.DESC))

        # Paging
        if f.page_size > 0:
            start = f.page * f.page_size
            result = result[start: start + f.page_size]

        # Hard limit
        if f.limit > 0:
            result = result[:f.limit]

        return result

    @staticmethod
    def _sort_key(sort_by: str):
        def key(r: HistoricalRecord):
            if sort_by == "timestamp":
                return r.timestamp
            if sort_by == "symbol":
                return r.symbol
            if sort_by == "sequence":
                return r.sequence
            return r.timestamp
        return key
