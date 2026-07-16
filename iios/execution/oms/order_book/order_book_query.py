"""iios/execution/oms/order_book/order_book_query.py
==================================================
OrderBookQuery — executes filter-based queries against
an in-memory collection of OrderBookEntry objects.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from iios.execution.oms.order_book.constants import QuerySortField
from iios.execution.oms.order_book.order_book_entry import OrderBookEntry
from iios.execution.oms.order_book.order_book_filter import OrderBookFilter


@dataclass(frozen=True)
class QueryResult:
    """Immutable result of an Order Book query."""

    entries:       tuple[OrderBookEntry, ...]
    total_matched: int
    query_time_ms: float
    filter_applied: bool

    @property
    def count(self) -> int:
        return len(self.entries)

    @property
    def is_empty(self) -> bool:
        return self.count == 0

    @property
    def has_more(self) -> bool:
        """True if pagination truncated results."""
        return self.total_matched > self.count

    def to_dict(self) -> dict[str, Any]:
        return {
            "count":          self.count,
            "total_matched":  self.total_matched,
            "query_time_ms":  round(self.query_time_ms, 3),
            "filter_applied": self.filter_applied,
            "has_more":       self.has_more,
        }


# ── Sort key extractors ───────────────────────────────────────────────────────

_SORT_KEY: dict[QuerySortField, Callable[[OrderBookEntry], Any]] = {
    QuerySortField.ADDED_AT:   lambda e: e.added_at,
    QuerySortField.UPDATED_AT: lambda e: e.updated_at,
    QuerySortField.ORDER_ID:   lambda e: e.order_id,
    QuerySortField.STATUS:     lambda e: e.status.value,
    QuerySortField.INSTRUMENT: lambda e: e.instrument,
}


class OrderBookQuery:
    """
    Stateless query executor for OrderBookEntry collections.

    Thread-safe (no mutable state).
    """

    def execute(
        self,
        entries:    Sequence[OrderBookEntry],
        book_filter: OrderBookFilter | None = None,
    ) -> QueryResult:
        """
        Apply *book_filter* to *entries* and return a QueryResult.

        Parameters
        ----------
        entries     : All entries to scan (usually from the registry).
        book_filter : Filter specification. None = return all entries.
        """
        t0 = time.time()

        if book_filter is None:
            matched = list(entries)
        else:
            matched = [e for e in entries if book_filter.matches(e)]

        total_matched = len(matched)

        if book_filter is not None:
            # Sort
            sort_key = _SORT_KEY.get(book_filter.sort_by, lambda e: e.added_at)
            matched.sort(key=sort_key, reverse=book_filter.descending)
            # Paginate
            offset = book_filter.offset
            limit  = book_filter.limit
            if offset:
                matched = matched[offset:]
            if limit is not None:
                matched = matched[:limit]

        query_ms = (time.time() - t0) * 1_000
        return QueryResult(
            entries        = tuple(matched),
            total_matched  = total_matched,
            query_time_ms  = query_ms,
            filter_applied = book_filter is not None,
        )

    def find_by_id(
        self,
        entries:  dict[str, OrderBookEntry],
        order_id: str,
    ) -> OrderBookEntry | None:
        """O(1) lookup by order_id."""
        return entries.get(order_id)

    def count_by_status(
        self,
        entries: Sequence[OrderBookEntry],
    ) -> dict[str, int]:
        """Count entries per BookEntryStatus."""
        counts: dict[str, int] = {}
        for e in entries:
            key = e.status.value
            counts[key] = counts.get(key, 0) + 1
        return counts
