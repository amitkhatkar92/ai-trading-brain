"""iios/execution/oms/order_book/__init__.py
==================================================
Public API for the IIOS Order Book.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

from iios.execution.oms.order_book.constants import (
    BOOK_SYSTEM_ID, REGISTRY_SYSTEM_ID, FACTORY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID, INDEX_SYSTEM_ID, VERSION,
    ACTOR_SYSTEM, ACTOR_BOOK, ACTOR_REGISTRY, ACTOR_FACTORY, ACTOR_USER,
    DEFAULT_MAX_ENTRIES, DEFAULT_MAX_HISTORY, DEFAULT_MAX_SNAPSHOT_AGE,
    BookEntryStatus, ORDER_STATE_TO_BOOK_STATUS, TERMINAL_BOOK_STATUSES,
    BookEventType, BookValidationCode, QuerySortField,
)
from iios.execution.oms.order_book.exceptions import (
    OrderBookError, OrderBookEntryError, OrderEntryNotFoundError,
    DuplicateEntryError, OrderBookCapacityError, OrderBookNotRunning,
    OrderBookValidationError, OrderBookIndexError, OrderBookSnapshotError,
    OrderBookQueryError, OrderBookHistoryError,
)
from iios.execution.oms.order_book.order_book_entry import OrderBookEntry
from iios.execution.oms.order_book.order_book_index import OrderBookIndex
from iios.execution.oms.order_book.order_book_filter import (
    OrderBookFilter,
    active_filter, completed_filter, cancelled_filter, rejected_filter,
    strategy_filter, portfolio_filter, instrument_filter,
)
from iios.execution.oms.order_book.order_book_query import OrderBookQuery, QueryResult
from iios.execution.oms.order_book.order_book_context import (
    OrderBookContext, OrderAddRequest, OrderUpdateRequest,
)
from iios.execution.oms.order_book.order_book_snapshot import (
    OrderBookSnapshot, FilteredSnapshot, HistoricalSnapshot,
)
from iios.execution.oms.order_book.order_book_events import (
    OrderBookEvent, make_book_event,
)
from iios.execution.oms.order_book.order_book_history import (
    BookHistoryEntry, OrderBookHistory,
)
from iios.execution.oms.order_book.order_book_statistics import OrderBookStatistics
from iios.execution.oms.order_book.order_book_validation import (
    BookValidationResult, OrderBookValidator,
)
from iios.execution.oms.order_book.order_book_factory import OrderBookEntryFactory
from iios.execution.oms.order_book.order_book_registry import OrderBookRegistry
from iios.execution.oms.order_book.order_book import OrderBook

__all__ = [
    "BOOK_SYSTEM_ID", "REGISTRY_SYSTEM_ID", "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID", "INDEX_SYSTEM_ID", "VERSION",
    "ACTOR_SYSTEM", "ACTOR_BOOK", "ACTOR_REGISTRY", "ACTOR_FACTORY", "ACTOR_USER",
    "DEFAULT_MAX_ENTRIES", "DEFAULT_MAX_HISTORY", "DEFAULT_MAX_SNAPSHOT_AGE",
    "BookEntryStatus", "ORDER_STATE_TO_BOOK_STATUS", "TERMINAL_BOOK_STATUSES",
    "BookEventType", "BookValidationCode", "QuerySortField",
    "OrderBookError", "OrderBookEntryError", "OrderEntryNotFoundError",
    "DuplicateEntryError", "OrderBookCapacityError", "OrderBookNotRunning",
    "OrderBookValidationError", "OrderBookIndexError", "OrderBookSnapshotError",
    "OrderBookQueryError", "OrderBookHistoryError",
    "OrderBookEntry", "OrderBookIndex",
    "OrderBookFilter",
    "active_filter", "completed_filter", "cancelled_filter", "rejected_filter",
    "strategy_filter", "portfolio_filter", "instrument_filter",
    "OrderBookQuery", "QueryResult",
    "OrderBookContext", "OrderAddRequest", "OrderUpdateRequest",
    "OrderBookSnapshot", "FilteredSnapshot", "HistoricalSnapshot",
    "OrderBookEvent", "make_book_event",
    "BookHistoryEntry", "OrderBookHistory",
    "OrderBookStatistics",
    "BookValidationResult", "OrderBookValidator",
    "OrderBookEntryFactory",
    "OrderBookRegistry",
    "OrderBook",
]
