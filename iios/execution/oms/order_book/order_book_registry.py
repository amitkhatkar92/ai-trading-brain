"""iios/execution/oms/order_book/order_book_registry.py
==================================================
OrderBookRegistry — IIOS v1.0 thread-safe store of OrderBookEntry
objects with multi-dimensional indexing, querying, and history.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    BookEntryStatus,
    BookEventType,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_HISTORY,
    REGISTRY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    DuplicateEntryError,
    OrderBookCapacityError,
    OrderBookNotRunning,
    OrderEntryNotFoundError,
)
from .order_book_context import OrderAddRequest, OrderUpdateRequest
from .order_book_entry import OrderBookEntry
from .order_book_events import OrderBookEvent, make_book_event
from .order_book_filter import OrderBookFilter
from .order_book_history import BookHistoryEntry, OrderBookHistory
from .order_book_index import OrderBookIndex
from .order_book_query import OrderBookQuery, QueryResult
from .order_book_snapshot import FilteredSnapshot, HistoricalSnapshot, OrderBookSnapshot
from .order_book_statistics import OrderBookStatistics

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID,
                          component="OrderBookRegistry")


class OrderBookRegistry(LifecycleAwareMixin):
    """
    IIOS v1.0 internal order repository.

    Thread-safe. Lifecycle-aware.
    Owns the index, history, query executor, and statistics.
    """

    SYSTEM_ID = REGISTRY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._entries:  dict[str, OrderBookEntry] = {}
        self._max_entries = max_entries
        self._index     = OrderBookIndex()
        self._history   = OrderBookHistory(max_entries=DEFAULT_MAX_HISTORY * 10)
        self._query     = OrderBookQuery()
        self._stats     = OrderBookStatistics()
        self._lock      = threading.RLock()
        self._listeners: list[Callable[[OrderBookEvent], None]] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("OrderBookRegistry started.", capacity=self._max_entries)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("OrderBookRegistry stopped.", entries=len(self._entries))

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise OrderBookNotRunning("OrderBookRegistry must be started before use.")

    # ── Add ───────────────────────────────────────────────────────────────────

    def add(
        self,
        entry:     OrderBookEntry,
        overwrite: bool = False,
    ) -> OrderBookEntry:
        self._assert_running()
        oid = entry.order_id
        with self._lock:
            if oid in self._entries and not overwrite:
                raise DuplicateEntryError(oid)
            if len(self._entries) >= self._max_entries and oid not in self._entries:
                raise OrderBookCapacityError(
                    f"Order book capacity reached ({self._max_entries})"
                )
            self._entries[oid] = entry
            self._index.add(entry.to_dict())

        self._stats.record_added()
        self._history.record(BookHistoryEntry(
            order_id  = oid,
            operation = "ADD",
            new_status = entry.status.value,
            new_state  = entry.order_state,
            actor      = "iios:book",
        ))
        _log.info("Order added to book.", order_id=oid, instrument=entry.instrument)
        self._dispatch(make_book_event(
            BookEventType.ORDER_ADDED,
            oid,
            instrument = entry.instrument,
            status     = entry.status,
        ))
        return entry

    # ── Update ────────────────────────────────────────────────────────────────

    def update(
        self,
        request: OrderUpdateRequest,
    ) -> OrderBookEntry:
        self._assert_running()
        with self._lock:
            entry = self._get_or_raise(request.order_id)
            old_status = entry.status.value
            entry.apply_state_update(
                request.new_order_state,
                filled_quantity = request.filled_quantity,
                average_price   = request.average_price,
            )
            new_status = entry.status.value
            if old_status != new_status:
                self._index.update_status(request.order_id, old_status, new_status)
                self._stats.record_status_change(old_status, new_status)

        self._history.record(BookHistoryEntry(
            order_id   = request.order_id,
            operation  = "UPDATE",
            old_status = old_status,
            new_status = new_status,
            old_state  = "",
            new_state  = request.new_order_state,
            actor      = request.actor,
            reason     = request.reason,
        ))
        self._dispatch(make_book_event(
            BookEventType.ORDER_UPDATED,
            request.order_id,
            instrument = entry.instrument,
            status     = entry.status,
        ))
        return entry

    # ── Remove ────────────────────────────────────────────────────────────────

    def remove(self, order_id: str, *, actor: str = ACTOR_SYSTEM) -> OrderBookEntry:
        self._assert_running()
        with self._lock:
            entry = self._get_or_raise(order_id)
            del self._entries[order_id]
            self._index.remove(entry.to_dict())

        self._stats.record_removed()
        self._history.record(BookHistoryEntry(
            order_id  = order_id,
            operation = "REMOVE",
            old_status = entry.status.value,
            actor      = actor,
        ))
        self._dispatch(make_book_event(BookEventType.ORDER_REMOVED, order_id))
        return entry

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, order_id: str) -> OrderBookEntry:
        self._assert_running()
        t0 = time.time()
        with self._lock:
            entry = self._entries.get(order_id)
        self._stats.record_lookup((time.time() - t0) * 1_000)
        if entry is None:
            raise OrderEntryNotFoundError(order_id)
        return entry

    def contains(self, order_id: str) -> bool:
        with self._lock:
            return order_id in self._entries

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, book_filter: OrderBookFilter | None = None) -> QueryResult:
        self._assert_running()
        with self._lock:
            entries = list(self._entries.values())
        return self._query.execute(entries, book_filter)

    def find_active(self) -> list[OrderBookEntry]:
        from .order_book_filter import active_filter
        r = self.query(active_filter())
        return list(r.entries)

    def find_by_strategy(self, strategy_id: str) -> list[OrderBookEntry]:
        with self._lock:
            ids = self._index.lookup("strategy_id", strategy_id)
            return [self._entries[oid] for oid in ids if oid in self._entries]

    def find_by_portfolio(self, portfolio_id: str) -> list[OrderBookEntry]:
        with self._lock:
            ids = self._index.lookup("portfolio_id", portfolio_id)
            return [self._entries[oid] for oid in ids if oid in self._entries]

    def find_by_instrument(self, instrument: str) -> list[OrderBookEntry]:
        with self._lock:
            ids = self._index.lookup("instrument", instrument)
            return [self._entries[oid] for oid in ids if oid in self._entries]

    def find_by_broker(self, broker_id: str) -> list[OrderBookEntry]:
        with self._lock:
            ids = self._index.lookup("broker_id", broker_id)
            return [self._entries[oid] for oid in ids if oid in self._entries]

    def find_by_status(self, status: BookEntryStatus) -> list[OrderBookEntry]:
        with self._lock:
            ids = self._index.lookup("status", status.value)
            return [self._entries[oid] for oid in ids if oid in self._entries]

    def all_order_ids(self) -> list[str]:
        with self._lock:
            return list(self._entries.keys())

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def snapshot(self) -> OrderBookSnapshot:
        self._assert_running()
        with self._lock:
            entries = list(self._entries.values())
            idx_util = self._index.utilization()
        counts: dict[str, int] = {}
        for e in entries:
            k = e.status.value
            counts[k] = counts.get(k, 0) + 1
        snap = OrderBookSnapshot(
            total_entries   = len(entries),
            active_count    = counts.get("ACTIVE",    0),
            completed_count = counts.get("COMPLETED", 0),
            cancelled_count = counts.get("CANCELLED", 0),
            rejected_count  = counts.get("REJECTED",  0),
            expired_count   = counts.get("EXPIRED",   0),
            failed_count    = counts.get("FAILED",    0),
            unique_instruments = idx_util.get("instrument", 0),
            unique_strategies  = idx_util.get("strategy_id", 0),
            unique_portfolios  = idx_util.get("portfolio_id", 0),
            unique_brokers     = idx_util.get("broker_id", 0),
        )
        self._stats.record_snapshot()
        self._dispatch(make_book_event(
            BookEventType.SNAPSHOT_CREATED, "",
            reason="book snapshot",
        ))
        return snap

    def filtered_snapshot(
        self,
        book_filter: OrderBookFilter,
    ) -> FilteredSnapshot:
        self._assert_running()
        result = self.query(book_filter)
        snap = FilteredSnapshot(
            filter_summary = book_filter.to_dict(),
            entries        = tuple(e.to_dict() for e in result.entries),
            total_matched  = result.total_matched,
            query_time_ms  = result.query_time_ms,
        )
        self._stats.record_snapshot()
        self._dispatch(make_book_event(BookEventType.SNAPSHOT_CREATED, ""))
        return snap

    def historical_snapshot(
        self,
        since: float,
        until: Optional[float] = None,
    ) -> HistoricalSnapshot:
        self._assert_running()
        end = until or time.time()
        history_entries = self._history.since(since)
        in_window = [
            e.to_dict() for e in history_entries
            if e.occurred_at <= end
        ]
        snap = HistoricalSnapshot(
            window_start = since,
            window_end   = end,
            entries      = tuple(in_window),
        )
        self._stats.record_snapshot()
        return snap

    # ── History ───────────────────────────────────────────────────────────────

    def history(self) -> OrderBookHistory:
        return self._history

    def history_for_order(self, order_id: str) -> list[BookHistoryEntry]:
        return self._history.for_order(order_id)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> OrderBookStatistics:
        return self._stats

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[OrderBookEvent], None]) -> None:
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[OrderBookEvent], None]) -> None:
        with self._lock:
            self._listeners = [f for f in self._listeners if f != fn]

    def _dispatch(self, event: OrderBookEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                _log.warning("Book event listener raised — continuing.")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_raise(self, order_id: str) -> OrderBookEntry:
        entry = self._entries.get(order_id)
        if entry is None:
            raise OrderEntryNotFoundError(order_id)
        return entry
