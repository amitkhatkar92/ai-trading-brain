"""iios/execution/oms/order_book/order_book_filter.py
==================================================
OrderBookFilter — composable, immutable filter specification
for querying the Order Book.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Optional

from iios.execution.oms.order_book.constants import (
    BookEntryStatus,
    QuerySortField,
)
from iios.execution.oms.order_book.order_book_entry import OrderBookEntry


@dataclass(frozen=True)
class OrderBookFilter:
    """
    Immutable specification for filtering Order Book entries.

    All fields are optional; unset fields are ignored during matching.
    Multiple non-None fields are combined with AND.
    """

    # Identifier filters
    order_ids:     Optional[frozenset[str]]             = None
    portfolio_ids: Optional[frozenset[str]]             = None
    strategy_ids:  Optional[frozenset[str]]             = None
    decision_ids:  Optional[frozenset[str]]             = None
    execution_ids: Optional[frozenset[str]]             = None
    workflow_ids:  Optional[frozenset[str]]             = None
    broker_ids:    Optional[frozenset[str]]             = None

    # Instrument filters
    instruments:   Optional[frozenset[str]]             = None
    exchanges:     Optional[frozenset[str]]             = None

    # Status / type filters
    statuses:      Optional[frozenset[BookEntryStatus]] = None
    order_types:   Optional[frozenset[str]]             = None
    sides:         Optional[frozenset[str]]             = None

    # Time range
    added_after:   Optional[float] = None
    added_before:  Optional[float] = None
    updated_after: Optional[float] = None

    # Quantity / fill
    min_fill_ratio: Optional[float] = None
    max_fill_ratio: Optional[float] = None

    # Pagination / sorting
    limit:          Optional[int]         = None
    offset:         int                   = 0
    sort_by:        QuerySortField        = QuerySortField.ADDED_AT
    descending:     bool                  = True

    # ── Matching ──────────────────────────────────────────────────────────────

    def matches(self, entry: OrderBookEntry) -> bool:
        """Return True if *entry* satisfies every non-None filter criterion."""
        if self.order_ids     and entry.order_id     not in self.order_ids:     return False
        if self.portfolio_ids and entry.portfolio_id not in self.portfolio_ids: return False
        if self.strategy_ids  and entry.strategy_id  not in self.strategy_ids:  return False
        if self.decision_ids  and entry.decision_id  not in self.decision_ids:  return False
        if self.execution_ids and entry.execution_id not in self.execution_ids: return False
        if self.workflow_ids  and entry.workflow_id  not in self.workflow_ids:  return False
        if self.broker_ids    and entry.broker_id    not in self.broker_ids:    return False
        if self.instruments   and entry.instrument   not in self.instruments:   return False
        if self.exchanges     and entry.exchange     not in self.exchanges:      return False
        if self.statuses      and entry.status       not in self.statuses:      return False
        if self.order_types   and entry.order_type   not in self.order_types:   return False
        if self.sides         and entry.side         not in self.sides:          return False
        if self.added_after   is not None and entry.added_at   < self.added_after:   return False
        if self.added_before  is not None and entry.added_at   > self.added_before:  return False
        if self.updated_after is not None and entry.updated_at < self.updated_after: return False
        if self.min_fill_ratio is not None and entry.fill_ratio < self.min_fill_ratio: return False
        if self.max_fill_ratio is not None and entry.fill_ratio > self.max_fill_ratio: return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_ids":      sorted(self.order_ids)     if self.order_ids     else None,
            "portfolio_ids":  sorted(self.portfolio_ids) if self.portfolio_ids else None,
            "strategy_ids":   sorted(self.strategy_ids)  if self.strategy_ids  else None,
            "statuses":       [s.value for s in self.statuses] if self.statuses else None,
            "instruments":    sorted(self.instruments)   if self.instruments   else None,
            "sort_by":        self.sort_by.value,
            "descending":     self.descending,
            "limit":          self.limit,
            "offset":         self.offset,
        }


# ── Pre-built filter factories ────────────────────────────────────────────────

def active_filter(limit: Optional[int] = None) -> OrderBookFilter:
    return OrderBookFilter(
        statuses = frozenset({BookEntryStatus.ACTIVE}),
        limit    = limit,
    )


def completed_filter(limit: Optional[int] = None) -> OrderBookFilter:
    return OrderBookFilter(
        statuses = frozenset({BookEntryStatus.COMPLETED}),
        limit    = limit,
    )


def cancelled_filter(limit: Optional[int] = None) -> OrderBookFilter:
    return OrderBookFilter(
        statuses = frozenset({BookEntryStatus.CANCELLED}),
        limit    = limit,
    )


def rejected_filter(limit: Optional[int] = None) -> OrderBookFilter:
    return OrderBookFilter(
        statuses = frozenset({BookEntryStatus.REJECTED}),
        limit    = limit,
    )


def strategy_filter(strategy_id: str, limit: Optional[int] = None) -> OrderBookFilter:
    return OrderBookFilter(
        strategy_ids = frozenset({strategy_id}),
        limit        = limit,
    )


def portfolio_filter(portfolio_id: str, limit: Optional[int] = None) -> OrderBookFilter:
    return OrderBookFilter(
        portfolio_ids = frozenset({portfolio_id}),
        limit         = limit,
    )


def instrument_filter(instrument: str, limit: Optional[int] = None) -> OrderBookFilter:
    return OrderBookFilter(
        instruments = frozenset({instrument}),
        limit       = limit,
    )
