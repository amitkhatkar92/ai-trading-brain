"""iios/execution/oms/order_book/order_book.py
==================================================
OrderBook — IIOS v1.0 primary entry point for the internal
Order Book.

Owns the registry and provides the full book API.

IIOS v1.0: LifecycleAwareMixin, logging, audit.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    BOOK_SYSTEM_ID,
    DEFAULT_MAX_ENTRIES,
    BookEntryStatus,
    BookEventType,
    VERSION,
)
from .exceptions import OrderBookNotRunning, OrderEntryNotFoundError
from .order_book_context import OrderAddRequest, OrderUpdateRequest
from .order_book_entry import OrderBookEntry
from .order_book_events import OrderBookEvent, make_book_event
from .order_book_factory import OrderBookEntryFactory
from .order_book_filter import OrderBookFilter
from .order_book_history import BookHistoryEntry, OrderBookHistory
from .order_book_query import QueryResult
from .order_book_registry import OrderBookRegistry
from .order_book_snapshot import FilteredSnapshot, HistoricalSnapshot, OrderBookSnapshot
from .order_book_statistics import OrderBookStatistics
from .order_book_validation import BookValidationResult, OrderBookValidator

_log   = get_logger(__name__, engine_id=BOOK_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=BOOK_SYSTEM_ID, component="OrderBook")


class OrderBook(LifecycleAwareMixin):
    """
    IIOS v1.0 institutional internal order book.

    Stores every order known to IIOS.
    Provides fast retrieval, multi-dimensional indexing,
    composable querying, and immutable snapshots.

    Does NOT: route, execute, communicate with brokers,
    or implement market depth.
    """

    SYSTEM_ID = BOOK_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._registry  = OrderBookRegistry(max_entries=max_entries)
        self._factory   = OrderBookEntryFactory()
        self._validator = OrderBookValidator()
        self._started_at: float = 0.0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        self._started_at = time.time()
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("OrderBook started.")

    def _on_stop(self) -> None:
        if self._registry.is_running:
            self._registry.stop()
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("OrderBook stopped.")

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise OrderBookNotRunning("OrderBook must be started before use.")

    # ── Add ───────────────────────────────────────────────────────────────────

    def add(self, request: OrderAddRequest) -> OrderBookEntry:
        """Validate and add a new order to the book."""
        self._assert_running()
        existing = frozenset(self._registry.all_order_ids())
        val = self._validator.validate_add_request(request, existing)
        if not val:
            from .exceptions import OrderBookValidationError
            raise OrderBookValidationError(
                "Order book add validation failed.",
                errors=val.errors,
            )
        entry = self._factory.create(request)
        return self._registry.add(entry)

    def add_from_params(
        self,
        order_id:     str,
        instrument:   str = "",
        exchange:     str = "",
        order_type:   str = "",
        side:         str = "",
        portfolio_id: str = "",
        strategy_id:  str = "",
        workflow_id:  str = "",
        execution_id: str = "",
        order_state:  str = "",
        **kwargs: Any,
    ) -> OrderBookEntry:
        """Convenience: add order from named parameters."""
        req = OrderAddRequest(
            order_id     = order_id,
            instrument   = instrument,
            exchange     = exchange,
            order_type   = order_type,
            side         = side,
            portfolio_id = portfolio_id,
            strategy_id  = strategy_id,
            workflow_id  = workflow_id,
            execution_id = execution_id,
            order_state  = order_state,
        )
        return self.add(req)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, request: OrderUpdateRequest) -> OrderBookEntry:
        """Update an existing order's state."""
        self._assert_running()
        return self._registry.update(request)

    def update_state(
        self,
        order_id:        str,
        new_order_state: str,
        *,
        actor:  str = "iios:system",
        reason: str = "",
    ) -> OrderBookEntry:
        """Convenience: update order state."""
        return self.update(OrderUpdateRequest(
            order_id        = order_id,
            new_order_state = new_order_state,
            actor           = actor,
            reason          = reason,
        ))

    # ── Remove ────────────────────────────────────────────────────────────────

    def remove(self, order_id: str) -> OrderBookEntry:
        self._assert_running()
        return self._registry.remove(order_id)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, order_id: str) -> OrderBookEntry:
        self._assert_running()
        return self._registry.get(order_id)

    def contains(self, order_id: str) -> bool:
        return self._registry.contains(order_id)

    def count(self) -> int:
        return self._registry.count()

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, book_filter: OrderBookFilter | None = None) -> QueryResult:
        self._assert_running()
        return self._registry.query(book_filter)

    def find_active(self) -> list[OrderBookEntry]:
        return self._registry.find_active()

    def find_completed(self) -> list[OrderBookEntry]:
        return self._registry.find_by_status(BookEntryStatus.COMPLETED)

    def find_cancelled(self) -> list[OrderBookEntry]:
        return self._registry.find_by_status(BookEntryStatus.CANCELLED)

    def find_rejected(self) -> list[OrderBookEntry]:
        return self._registry.find_by_status(BookEntryStatus.REJECTED)

    def find_by_strategy(self, strategy_id: str) -> list[OrderBookEntry]:
        return self._registry.find_by_strategy(strategy_id)

    def find_by_portfolio(self, portfolio_id: str) -> list[OrderBookEntry]:
        return self._registry.find_by_portfolio(portfolio_id)

    def find_by_instrument(self, instrument: str) -> list[OrderBookEntry]:
        return self._registry.find_by_instrument(instrument)

    def find_by_broker(self, broker_id: str) -> list[OrderBookEntry]:
        return self._registry.find_by_broker(broker_id)

    def find_by_status(self, status: BookEntryStatus) -> list[OrderBookEntry]:
        return self._registry.find_by_status(status)

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def snapshot(self) -> OrderBookSnapshot:
        self._assert_running()
        return self._registry.snapshot()

    def filtered_snapshot(self, book_filter: OrderBookFilter) -> FilteredSnapshot:
        self._assert_running()
        return self._registry.filtered_snapshot(book_filter)

    def historical_snapshot(
        self,
        since: float,
        until: Optional[float] = None,
    ) -> HistoricalSnapshot:
        self._assert_running()
        return self._registry.historical_snapshot(since, until)

    # ── History ───────────────────────────────────────────────────────────────

    def history_for_order(self, order_id: str) -> list[BookHistoryEntry]:
        return self._registry.history_for_order(order_id)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> OrderBookStatistics:
        return self._registry.statistics()

    # ── Validation ───────────────────────────────────────────────────────────

    def validate(self) -> BookValidationResult:
        """Validate the entire book for consistency."""
        self._assert_running()
        # Check active index vs actual entries
        active_ids = self._registry._index.lookup("status", BookEntryStatus.ACTIVE.value)
        result = self._validator.validate_index_consistency(
            self._registry._entries,
            active_ids,
        )
        if result.passed:
            self._registry._dispatch(make_book_event(
                BookEventType.BOOK_VALIDATED, "", reason="validation passed",
            ))
        return result

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[OrderBookEvent], None]) -> None:
        self._registry.add_listener(fn)

    def remove_listener(self, fn: Callable[[OrderBookEvent], None]) -> None:
        self._registry.remove_listener(fn)

    # ── Misc ──────────────────────────────────────────────────────────────────

    @property
    def uptime_sec(self) -> float:
        if self._started_at == 0.0:
            return 0.0
        return time.time() - self._started_at
