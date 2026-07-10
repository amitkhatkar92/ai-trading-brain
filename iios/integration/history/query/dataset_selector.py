"""iios/integration/history/query/dataset_selector.py

Selects the best dataset(s) for a given query based on metadata.
"""
from __future__ import annotations

import logging
from typing import Any

from iios.integration.history.core.historical_dataset import HistoricalDataset
from iios.integration.history.history_constants       import (
    DatasetStatus,
    HistoricalDataType,
)
from iios.integration.history.query.historical_filter import HistoricalFilter

logger = logging.getLogger(__name__)


class DatasetSelector:
    """
    Selects relevant datasets for a HistoricalFilter.

    Selection criteria (in priority order):
    1. Explicit dataset_ids in filter → use exactly those
    2. data_type match
    3. Symbol overlap
    4. Time range overlap
    5. Active status preferred
    """

    def select(
        self,
        all_datasets: list[HistoricalDataset],
        f:            HistoricalFilter,
    ) -> list[HistoricalDataset]:
        """
        Return datasets from ``all_datasets`` that could satisfy filter ``f``.
        """
        # 1. Explicit dataset_ids
        if f.dataset_ids:
            candidates = [d for d in all_datasets if d.dataset_id in set(f.dataset_ids)]
            return candidates

        candidates = list(all_datasets)

        # 2. Data type
        if f.data_types:
            candidates = [d for d in candidates if d.data_type in f.data_types]

        # 3. Symbol overlap
        if f.symbols:
            def _overlaps_symbols(ds: HistoricalDataset) -> bool:
                if not ds.symbols:
                    return True   # unknown → include
                return bool(set(f.symbols) & set(ds.symbols))
            candidates = [d for d in candidates if _overlaps_symbols(d)]

        # 4. Time range overlap
        if f.start_ts is not None and f.end_ts is not None:
            def _overlaps_time(ds: HistoricalDataset) -> bool:
                if ds.start_ts == 0.0 and ds.end_ts == 0.0:
                    return True   # unknown → include
                return ds.start_ts <= f.end_ts and ds.end_ts >= f.start_ts
            candidates = [d for d in candidates if _overlaps_time(d)]

        # 5. Prefer active datasets
        active = [d for d in candidates if d.status == DatasetStatus.ACTIVE]
        return active if active else candidates
