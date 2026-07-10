"""iios/integration/history/query/historical_filter.py

Composable filter primitives for historical queries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import (
    HistoricalDataType,
    QueryOperator,
    SortOrder,
)


@dataclass
class FieldFilter:
    """
    Single field-level predicate: field OPERATOR value.

    Examples:
        FieldFilter("symbol",    QueryOperator.EQ,      "AAPL")
        FieldFilter("timestamp", QueryOperator.BETWEEN, (1_700_000_000, 1_700_086_400))
        FieldFilter("value",     QueryOperator.GTE,     100.0)
    """
    field:    str          = ""
    operator: QueryOperator = QueryOperator.EQ
    value:    Any          = None

    def matches(self, record_dict: dict[str, Any]) -> bool:
        """Return True if the record satisfies this filter."""
        v = record_dict.get(self.field)
        if v is None:
            return False
        try:
            match self.operator:
                case QueryOperator.EQ:
                    return v == self.value
                case QueryOperator.NE:
                    return v != self.value
                case QueryOperator.GT:
                    return v > self.value
                case QueryOperator.LT:
                    return v < self.value
                case QueryOperator.GTE:
                    return v >= self.value
                case QueryOperator.LTE:
                    return v <= self.value
                case QueryOperator.IN:
                    return v in self.value
                case QueryOperator.NOT_IN:
                    return v not in self.value
                case QueryOperator.CONTAINS:
                    return str(self.value).lower() in str(v).lower()
                case QueryOperator.BETWEEN:
                    lo, hi = self.value
                    return lo <= v <= hi
                case _:
                    return False
        except (TypeError, ValueError):
            return False


@dataclass
class HistoricalFilter:
    """
    Compound filter for historical record queries.

    All conditions are AND-ed together.
    """
    # Standard top-level filters
    dataset_ids:  list[str]              = field(default_factory=list)
    data_types:   list[HistoricalDataType] = field(default_factory=list)
    symbols:      list[str]              = field(default_factory=list)
    start_ts:     float | None           = None
    end_ts:       float | None           = None
    tags:         list[str]              = field(default_factory=list)
    # Custom field predicates applied to record.data
    field_filters: list[FieldFilter]     = field(default_factory=list)
    # Result shaping
    limit:        int                    = 0
    page_size:    int                    = 1_000
    page:         int                    = 0
    sort_by:      str                    = "timestamp"
    sort_order:   SortOrder              = SortOrder.ASC

    def matches_record(self, record: Any) -> bool:
        """Return True if a HistoricalRecord satisfies all filter conditions."""
        if self.symbols and record.symbol not in self.symbols:
            return False
        if self.data_types and record.data_type not in self.data_types:
            return False
        if self.start_ts is not None and record.timestamp < self.start_ts:
            return False
        if self.end_ts is not None and record.timestamp > self.end_ts:
            return False
        if self.tags:
            if not any(t in record.tags for t in self.tags):
                return False
        # Custom field filters against record.data
        for ff in self.field_filters:
            if not ff.matches(record.data):
                return False
        return True
