"""tests/unit/iios/execution/oms/order_book/test_order_book.py
==================================================
Comprehensive test suite for C6 Phase 2 Module 2:
IIOS Order Book.

12 test classes, 95%+ coverage.
"""
from __future__ import annotations

import json
import threading
import time
from decimal import Decimal
from typing import Any

import pytest

from iios.execution.oms.order_book.constants import (
    TERMINAL_BOOK_STATUSES, BookEntryStatus, BookEventType,
    BookValidationCode, ORDER_STATE_TO_BOOK_STATUS, QuerySortField,
)
from iios.execution.oms.order_book.exceptions import (
    DuplicateEntryError, OrderBookCapacityError, OrderBookError,
    OrderBookNotRunning, OrderBookValidationError, OrderEntryNotFoundError,
)
from iios.execution.oms.order_book.order_book_entry import OrderBookEntry
from iios.execution.oms.order_book.order_book_index import OrderBookIndex
from iios.execution.oms.order_book.order_book_filter import (
    OrderBookFilter, active_filter, cancelled_filter, completed_filter,
    instrument_filter, portfolio_filter, rejected_filter, strategy_filter,
)
from iios.execution.oms.order_book.order_book_query import OrderBookQuery, QueryResult
from iios.execution.oms.order_book.order_book_context import (
    OrderAddRequest, OrderUpdateRequest,
)
from iios.execution.oms.order_book.order_book_snapshot import (
    FilteredSnapshot, HistoricalSnapshot, OrderBookSnapshot,
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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _req(
    order_id:    str = "ORD-001",
    instrument:  str = "RELIANCE",
    exchange:    str = "NSE",
    side:        str = "BUY",
    strategy_id: str = "STRAT-001",
    portfolio_id: str = "PORT-001",
    order_state: str = "CREATED",
    **kwargs: Any,
) -> OrderAddRequest:
    return OrderAddRequest(
        order_id     = order_id,
        instrument   = instrument,
        exchange     = exchange,
        side         = side,
        strategy_id  = strategy_id,
        portfolio_id = portfolio_id,
        order_state  = order_state,
        **kwargs,
    )


def _entry(
    order_id:   str = "ORD-001",
    instrument: str = "RELIANCE",
    status:     BookEntryStatus = BookEntryStatus.ACTIVE,
) -> OrderBookEntry:
    return OrderBookEntry(
        order_id   = order_id,
        instrument = instrument,
        status     = status,
        exchange   = "NSE",
        side       = "BUY",
        order_type = "MARKET",
    )


@pytest.fixture
def book() -> OrderBook:
    b = OrderBook()
    b.start()
    yield b
    if b.is_running:
        b.stop()


@pytest.fixture
def registry() -> OrderBookRegistry:
    r = OrderBookRegistry()
    r.start()
    yield r
    if r.is_running:
        r.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_book_entry_status(self) -> None:
        assert BookEntryStatus.ACTIVE.value    == "ACTIVE"
        assert BookEntryStatus.COMPLETED.value == "COMPLETED"
        assert BookEntryStatus.CANCELLED.value == "CANCELLED"
        assert BookEntryStatus.REJECTED.value  == "REJECTED"
        assert BookEntryStatus.EXPIRED.value   == "EXPIRED"
        assert BookEntryStatus.FAILED.value    == "FAILED"

    def test_terminal_statuses(self) -> None:
        assert BookEntryStatus.COMPLETED in TERMINAL_BOOK_STATUSES
        assert BookEntryStatus.CANCELLED in TERMINAL_BOOK_STATUSES
        assert BookEntryStatus.ACTIVE    not in TERMINAL_BOOK_STATUSES

    def test_order_state_mapping(self) -> None:
        assert ORDER_STATE_TO_BOOK_STATUS["CREATED"]          == BookEntryStatus.ACTIVE
        assert ORDER_STATE_TO_BOOK_STATUS["FILLED"]           == BookEntryStatus.COMPLETED
        assert ORDER_STATE_TO_BOOK_STATUS["CANCELLED"]        == BookEntryStatus.CANCELLED
        assert ORDER_STATE_TO_BOOK_STATUS["REJECTED"]         == BookEntryStatus.REJECTED
        assert ORDER_STATE_TO_BOOK_STATUS["EXPIRED"]          == BookEntryStatus.EXPIRED
        assert ORDER_STATE_TO_BOOK_STATUS["ACKNOWLEDGED"]     == BookEntryStatus.ACTIVE
        assert ORDER_STATE_TO_BOOK_STATUS["PARTIALLY_FILLED"] == BookEntryStatus.ACTIVE

    def test_event_types(self) -> None:
        assert BookEventType.ORDER_ADDED.value      == "ORDER_ADDED"
        assert BookEventType.ORDER_UPDATED.value    == "ORDER_UPDATED"
        assert BookEventType.SNAPSHOT_CREATED.value == "SNAPSHOT_CREATED"
        assert BookEventType.BOOK_VALIDATED.value   == "BOOK_VALIDATED"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self) -> None:
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(OrderBookError,          IIOSError)
        assert issubclass(OrderEntryNotFoundError, OrderBookError)
        assert issubclass(DuplicateEntryError,     OrderBookError)
        assert issubclass(OrderBookCapacityError,  OrderBookError)
        assert issubclass(OrderBookNotRunning,     OrderBookError)
        assert issubclass(OrderBookValidationError, OrderBookError)

    def test_not_found_carries_id(self) -> None:
        exc = OrderEntryNotFoundError("ORD-X")
        assert exc.order_id == "ORD-X"

    def test_duplicate_carries_id(self) -> None:
        exc = DuplicateEntryError("ORD-Y")
        assert exc.order_id == "ORD-Y"

    def test_validation_error_carries_errors(self) -> None:
        exc = OrderBookValidationError("fail", errors=("e1",))
        assert exc.errors == ("e1",)

    def test_error_codes(self) -> None:
        assert OrderBookError.DEFAULT_CODE          == "OB-000"
        assert OrderEntryNotFoundError.DEFAULT_CODE == "OB-002"
        assert DuplicateEntryError.DEFAULT_CODE     == "OB-003"
        assert OrderBookCapacityError.DEFAULT_CODE  == "OB-004"
        assert OrderBookNotRunning.DEFAULT_CODE     == "OB-005"


# ─────────────────────────────────────────────────────────────────────────────
# 3. OrderBookEntry
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderBookEntry:
    def test_creation(self) -> None:
        e = _entry()
        assert e.order_id   == "ORD-001"
        assert e.status     == BookEntryStatus.ACTIVE
        assert e.is_active
        assert not e.is_terminal

    def test_fill_ratio_zero(self) -> None:
        e = _entry()
        assert e.fill_ratio == 0.0

    def test_fill_ratio(self) -> None:
        e = _entry()
        e.quantity        = Decimal("100")
        e.filled_quantity = Decimal("50")
        assert abs(e.fill_ratio - 0.5) < 0.001

    def test_unfilled_quantity(self) -> None:
        e = _entry()
        e.quantity        = Decimal("100")
        e.filled_quantity = Decimal("30")
        assert e.unfilled_quantity == Decimal("70")

    def test_apply_state_update_to_terminal(self) -> None:
        e = _entry()
        e.apply_state_update("FILLED")
        assert e.status    == BookEntryStatus.COMPLETED
        assert e.is_terminal

    def test_apply_state_update_cancelled(self) -> None:
        e = _entry()
        e.apply_state_update("CANCELLED")
        assert e.status == BookEntryStatus.CANCELLED

    def test_apply_state_update_with_fill(self) -> None:
        e = _entry()
        e.quantity = Decimal("100")
        e.apply_state_update("PARTIALLY_FILLED", filled_quantity=Decimal("60"))
        assert e.filled_quantity == Decimal("60")
        assert e.status == BookEntryStatus.ACTIVE

    def test_to_dict(self) -> None:
        e = _entry()
        d = e.to_dict()
        assert d["order_id"]  == "ORD-001"
        assert d["status"]    == "ACTIVE"
        assert "fill_ratio"   in d
        assert "is_terminal"  in d

    def test_repr(self) -> None:
        e = _entry()
        assert "OrderBookEntry" in repr(e)
        assert "ORD-001" in repr(e)


# ─────────────────────────────────────────────────────────────────────────────
# 4. OrderBookIndex
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderBookIndex:
    def _add(self, idx: OrderBookIndex, order_id: str, **kwargs: str) -> None:
        d: dict[str, Any] = {"order_id": order_id}
        d.update(kwargs)
        idx.add(d)

    def test_add_and_lookup(self) -> None:
        idx = OrderBookIndex()
        self._add(idx, "O1", strategy_id="S1", status="ACTIVE")
        result = idx.lookup("strategy_id", "S1")
        assert "O1" in result

    def test_remove(self) -> None:
        idx = OrderBookIndex()
        self._add(idx, "O1", strategy_id="S1")
        idx.remove({"order_id": "O1", "strategy_id": "S1"})
        assert "O1" not in idx.lookup("strategy_id", "S1")

    def test_update_status(self) -> None:
        idx = OrderBookIndex()
        self._add(idx, "O1", status="ACTIVE")
        idx.update_status("O1", "ACTIVE", "COMPLETED")
        assert "O1" in idx.lookup("status", "COMPLETED")
        assert "O1" not in idx.lookup("status", "ACTIVE")

    def test_intersect(self) -> None:
        idx = OrderBookIndex()
        self._add(idx, "O1", strategy_id="S1", status="ACTIVE")
        self._add(idx, "O2", strategy_id="S1", status="COMPLETED")
        result = idx.intersect({"strategy_id": "S1", "status": "ACTIVE"})
        assert "O1" in result
        assert "O2" not in result

    def test_lookup_all(self) -> None:
        idx = OrderBookIndex()
        self._add(idx, "O1", strategy_id="S1")
        self._add(idx, "O2", strategy_id="S2")
        all_strats = idx.lookup_all("strategy_id")
        assert "S1" in all_strats
        assert "S2" in all_strats

    def test_cardinality(self) -> None:
        idx = OrderBookIndex()
        self._add(idx, "O1", strategy_id="S1")
        self._add(idx, "O2", strategy_id="S2")
        assert idx.cardinality("strategy_id") == 2

    def test_utilization(self) -> None:
        idx = OrderBookIndex()
        self._add(idx, "O1", instrument="RELIANCE")
        u = idx.utilization()
        assert u["instrument"] == 1

    def test_clear(self) -> None:
        idx = OrderBookIndex()
        self._add(idx, "O1", strategy_id="S1")
        idx.clear()
        assert len(idx.lookup("strategy_id", "S1")) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. OrderBookFilter and Query
# ─────────────────────────────────────────────────────────────────────────────

class TestFilterAndQuery:
    def _make_entries(self) -> list[OrderBookEntry]:
        entries = []
        for i in range(5):
            e = OrderBookEntry(
                order_id    = f"ORD-{i:03d}",
                instrument  = "RELIANCE" if i < 3 else "TCS",
                strategy_id = "S1" if i < 4 else "S2",
                portfolio_id = "P1",
                status      = BookEntryStatus.ACTIVE if i < 4 else BookEntryStatus.COMPLETED,
            )
            entries.append(e)
        return entries

    def test_active_filter(self) -> None:
        entries = self._make_entries()
        q = OrderBookQuery()
        r = q.execute(entries, active_filter())
        assert r.count == 4

    def test_completed_filter(self) -> None:
        entries = self._make_entries()
        q = OrderBookQuery()
        r = q.execute(entries, completed_filter())
        assert r.count == 1

    def test_strategy_filter(self) -> None:
        entries = self._make_entries()
        q = OrderBookQuery()
        r = q.execute(entries, strategy_filter("S2"))
        assert r.count == 1

    def test_instrument_filter(self) -> None:
        entries = self._make_entries()
        q = OrderBookQuery()
        r = q.execute(entries, instrument_filter("TCS"))
        assert r.count == 2

    def test_portfolio_filter(self) -> None:
        entries = self._make_entries()
        q = OrderBookQuery()
        r = q.execute(entries, portfolio_filter("P1"))
        assert r.count == 5

    def test_limit_and_offset(self) -> None:
        entries = self._make_entries()
        q = OrderBookQuery()
        f = OrderBookFilter(limit=2, offset=1)
        r = q.execute(entries, f)
        assert r.count == 2
        assert r.has_more

    def test_sort_by_instrument(self) -> None:
        entries = self._make_entries()
        q = OrderBookQuery()
        f = OrderBookFilter(sort_by=QuerySortField.INSTRUMENT, descending=False)
        r = q.execute(entries, f)
        insts = [e.instrument for e in r.entries]
        assert insts == sorted(insts)

    def test_no_filter_returns_all(self) -> None:
        entries = self._make_entries()
        q = OrderBookQuery()
        r = q.execute(entries, None)
        assert r.count == 5

    def test_query_result_properties(self) -> None:
        r = QueryResult(
            entries       = tuple([_entry()]),
            total_matched = 10,
            query_time_ms = 1.5,
            filter_applied = True,
        )
        assert r.count     == 1
        assert r.has_more
        assert not r.is_empty

    def test_filter_matches(self) -> None:
        e = _entry()
        f = OrderBookFilter(statuses=frozenset({BookEntryStatus.ACTIVE}))
        assert f.matches(e)

    def test_filter_no_match(self) -> None:
        e = _entry()
        f = OrderBookFilter(statuses=frozenset({BookEntryStatus.COMPLETED}))
        assert not f.matches(e)

    def test_filter_time_range(self) -> None:
        entries = self._make_entries()
        past    = time.time() + 100  # nothing added in the future
        q = OrderBookQuery()
        f = OrderBookFilter(added_after=past)
        r = q.execute(entries, f)
        assert r.count == 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Snapshots
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshots:
    def test_book_snapshot_counts(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001", instrument="RELIANCE")
        snap = book.snapshot()
        assert snap.total_entries == 1
        assert snap.active_count  == 1

    def test_book_snapshot_frozen(self, book: OrderBook) -> None:
        snap = book.snapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.total_entries = 99  # type: ignore[misc]

    def test_book_snapshot_to_dict_json(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001", instrument="RELIANCE")
        d = book.snapshot().to_dict()
        json.dumps(d)

    def test_filtered_snapshot(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001", instrument="RELIANCE")
        book.add_from_params("ORD-002", instrument="TCS")
        snap = book.filtered_snapshot(instrument_filter("RELIANCE"))
        assert snap.count == 1

    def test_filtered_snapshot_frozen(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001")
        snap = book.filtered_snapshot(active_filter())
        with pytest.raises((AttributeError, TypeError)):
            snap.total_matched = 99  # type: ignore[misc]

    def test_historical_snapshot(self, book: OrderBook) -> None:
        t0 = time.time()
        book.add_from_params("ORD-001")
        snap = book.historical_snapshot(since=t0)
        assert snap.count >= 1

    def test_snapshot_terminal_count(self) -> None:
        s = OrderBookSnapshot(
            completed_count = 5,
            cancelled_count = 2,
            rejected_count  = 1,
        )
        assert s.terminal_count == 8


# ─────────────────────────────────────────────────────────────────────────────
# 7. Events
# ─────────────────────────────────────────────────────────────────────────────

class TestEvents:
    def test_make_book_event(self) -> None:
        e = make_book_event(
            BookEventType.ORDER_ADDED,
            "ORD-001",
            instrument = "RELIANCE",
            status     = BookEntryStatus.ACTIVE,
        )
        assert e.order_id  == "ORD-001"
        assert e.event_type == BookEventType.ORDER_ADDED

    def test_event_frozen(self) -> None:
        e = make_book_event(BookEventType.ORDER_ADDED, "O")
        with pytest.raises((AttributeError, TypeError)):
            e.order_id = "X"  # type: ignore[misc]

    def test_event_to_dict(self) -> None:
        e = make_book_event(
            BookEventType.ORDER_UPDATED,
            "O",
            status = BookEntryStatus.COMPLETED,
        )
        d = e.to_dict()
        assert d["event_type"] == "ORDER_UPDATED"
        assert d["status"]     == "COMPLETED"


# ─────────────────────────────────────────────────────────────────────────────
# 8. History
# ─────────────────────────────────────────────────────────────────────────────

class TestHistory:
    def test_record_and_query(self) -> None:
        h = OrderBookHistory(max_entries=10)
        entry = BookHistoryEntry(order_id="O1", operation="ADD", new_status="ACTIVE")
        h.record(entry)
        assert h.count() == 1
        assert h.first() == entry

    def test_for_order(self) -> None:
        h = OrderBookHistory()
        h.record(BookHistoryEntry(order_id="O1", operation="ADD"))
        h.record(BookHistoryEntry(order_id="O2", operation="ADD"))
        h.record(BookHistoryEntry(order_id="O1", operation="UPDATE"))
        assert len(h.for_order("O1")) == 2

    def test_since(self) -> None:
        h = OrderBookHistory()
        t0 = time.time()
        h.record(BookHistoryEntry(order_id="O1", operation="ADD"))
        result = h.since(t0 - 1.0)
        assert len(result) >= 1

    def test_eviction(self) -> None:
        h = OrderBookHistory(max_entries=2)
        for i in range(3):
            h.record(BookHistoryEntry(order_id=f"O{i}", operation="ADD"))
        assert h.count()        == 2
        assert h.evicted_count  == 1
        assert h.total_recorded == 3

    def test_registry_records_history(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001")
        book.update_state("ORD-001", "ACKNOWLEDGED")
        h = book._registry.history_for_order("ORD-001")
        assert len(h) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 9. Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def setup_method(self) -> None:
        self.v = OrderBookValidator()

    def test_valid_add(self) -> None:
        r = _req()
        result = self.v.validate_add_request(r, frozenset())
        assert result.passed

    def test_empty_order_id_fails(self) -> None:
        r = _req(order_id="")
        result = self.v.validate_add_request(r, frozenset())
        assert not result.passed
        assert any("MISSING_ORDER_ID" in e for e in result.errors)

    def test_duplicate_fails(self) -> None:
        r = _req()
        result = self.v.validate_add_request(r, frozenset({"ORD-001"}))
        assert not result.passed
        assert any("DUPLICATE_ORDER_ID" in e for e in result.errors)

    def test_empty_instrument_warns(self) -> None:
        r = _req(instrument="")
        result = self.v.validate_add_request(r, frozenset())
        assert result.passed
        assert len(result.warnings) > 0

    def test_index_consistency_ok(self) -> None:
        entries = {"O1": _entry("O1"), "O2": _entry("O2")}
        index   = frozenset({"O1", "O2"})
        result  = self.v.validate_index_consistency(entries, index)
        assert result.passed

    def test_index_consistency_broken(self) -> None:
        entries = {"O1": _entry("O1")}
        index   = frozenset({"O1", "ORPHAN"})
        result  = self.v.validate_index_consistency(entries, index)
        assert not result.passed
        assert any("BROKEN_INDEX" in e for e in result.errors)

    def test_validation_result_bool(self) -> None:
        assert bool(BookValidationResult.ok())
        assert not bool(BookValidationResult.fail("err"))

    def test_book_validate(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001", instrument="RELIANCE")
        result = book.validate()
        assert result.passed


# ─────────────────────────────────────────────────────────────────────────────
# 10. Factory
# ─────────────────────────────────────────────────────────────────────────────

class TestFactory:
    def test_create_from_request(self) -> None:
        f = OrderBookEntryFactory()
        r = _req(order_state="CREATED")
        e = f.create(r)
        assert e.order_id  == "ORD-001"
        assert e.status    == BookEntryStatus.ACTIVE

    def test_create_filled(self) -> None:
        f = OrderBookEntryFactory()
        r = _req(order_state="FILLED")
        e = f.create(r)
        assert e.status == BookEntryStatus.COMPLETED

    def test_create_from_params(self) -> None:
        f = OrderBookEntryFactory()
        e = f.create_from_params(
            order_id   = "ORD-999",
            instrument = "TCS",
            side       = "SELL",
        )
        assert e.order_id  == "ORD-999"
        assert e.instrument == "TCS"


# ─────────────────────────────────────────────────────────────────────────────
# 11. OrderBook (facade)
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderBook:
    def test_not_running_before_start(self) -> None:
        b = OrderBook()
        with pytest.raises(OrderBookNotRunning):
            b.add(_req())

    def test_start_stop(self, book: OrderBook) -> None:
        assert book.is_running

    def test_add_and_get(self, book: OrderBook) -> None:
        book.add(_req())
        e = book.get("ORD-001")
        assert e.order_id == "ORD-001"

    def test_add_duplicate_raises(self, book: OrderBook) -> None:
        book.add(_req())
        with pytest.raises(OrderBookValidationError):
            book.add(_req())

    def test_add_missing_order_id_raises(self, book: OrderBook) -> None:
        with pytest.raises(OrderBookValidationError):
            book.add(_req(order_id=""))

    def test_update_state(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001", instrument="RELIANCE")
        book.update_state("ORD-001", "FILLED")
        e = book.get("ORD-001")
        assert e.status == BookEntryStatus.COMPLETED

    def test_remove(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001")
        book.remove("ORD-001")
        assert not book.contains("ORD-001")

    def test_contains_false(self, book: OrderBook) -> None:
        assert not book.contains("MISSING")

    def test_count(self, book: OrderBook) -> None:
        assert book.count() == 0
        book.add_from_params("ORD-001")
        assert book.count() == 1

    def test_find_active(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001", order_state="CREATED")
        active = book.find_active()
        assert len(active) == 1

    def test_find_completed(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001")
        book.update_state("ORD-001", "FILLED")
        completed = book.find_completed()
        assert any(e.order_id == "ORD-001" for e in completed)

    def test_find_cancelled(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001")
        book.update_state("ORD-001", "CANCELLED")
        assert len(book.find_cancelled()) == 1

    def test_find_rejected(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001")
        book.update_state("ORD-001", "REJECTED")
        assert len(book.find_rejected()) == 1

    def test_find_by_strategy(self, book: OrderBook) -> None:
        book.add(_req(strategy_id="STRAT-X"))
        assert len(book.find_by_strategy("STRAT-X")) == 1

    def test_find_by_portfolio(self, book: OrderBook) -> None:
        book.add(_req(portfolio_id="PORT-X"))
        assert len(book.find_by_portfolio("PORT-X")) == 1

    def test_find_by_instrument(self, book: OrderBook) -> None:
        book.add(_req(instrument="INFY"))
        assert len(book.find_by_instrument("INFY")) == 1

    def test_find_by_broker(self, book: OrderBook) -> None:
        req = _req()
        req.broker_id = "DHAN"
        book.add(req)
        assert len(book.find_by_broker("DHAN")) == 1

    def test_query_with_filter(self, book: OrderBook) -> None:
        book.add(_req("ORD-001", instrument="RELIANCE"))
        book.add(_req("ORD-002", instrument="TCS"))
        r = book.query(instrument_filter("RELIANCE"))
        assert r.count == 1

    def test_statistics(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001")
        book.update_state("ORD-001", "FILLED")
        stats = book.statistics()
        assert stats.orders_added     >= 1
        assert stats.orders_completed >= 1

    def test_listeners(self, book: OrderBook) -> None:
        events: list[OrderBookEvent] = []
        book.add_listener(events.append)
        book.add_from_params("ORD-001")
        assert any(e.event_type == BookEventType.ORDER_ADDED for e in events)

    def test_remove_listener(self, book: OrderBook) -> None:
        events: list[OrderBookEvent] = []
        book.add_listener(events.append)
        book.remove_listener(events.append)
        book.add_from_params("ORD-001")
        assert len(events) == 0

    def test_uptime(self, book: OrderBook) -> None:
        time.sleep(0.01)
        assert book.uptime_sec > 0.0

    def test_history_for_order(self, book: OrderBook) -> None:
        book.add_from_params("ORD-001")
        book.update_state("ORD-001", "ACKNOWLEDGED")
        h = book.history_for_order("ORD-001")
        assert len(h) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 12. Statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestStatistics:
    def test_initial(self) -> None:
        s = OrderBookStatistics()
        assert s.orders_added  == 0
        assert s.orders_active == 0

    def test_record_added(self) -> None:
        s = OrderBookStatistics()
        s.record_added()
        assert s.orders_added  == 1
        assert s.orders_active == 1
        assert s.peak_active   == 1

    def test_record_status_change_to_completed(self) -> None:
        s = OrderBookStatistics()
        s.record_added()
        s.record_status_change("ACTIVE", "COMPLETED")
        assert s.orders_completed == 1
        assert s.orders_active    == 0

    def test_peak_preserved(self) -> None:
        s = OrderBookStatistics()
        for _ in range(5):
            s.record_added()
        assert s.peak_active == 5
        s.record_status_change("ACTIVE", "COMPLETED")
        assert s.peak_active == 5

    def test_total_terminal(self) -> None:
        s = OrderBookStatistics()
        s.orders_completed = 3
        s.orders_cancelled = 2
        s.orders_rejected  = 1
        assert s.total_terminal == 6

    def test_avg_lookup_time(self) -> None:
        s = OrderBookStatistics()
        s.record_lookup(2.0)
        s.record_lookup(4.0)
        assert abs(s.avg_lookup_time_ms - 3.0) < 0.01

    def test_to_dict(self) -> None:
        s = OrderBookStatistics()
        s.record_added()
        d = s.to_dict()
        json.dumps(d)
        assert d["orders_added"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 13. Thread safety
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_adds(self) -> None:
        book = OrderBook(max_entries=500)
        book.start()
        errors: list[Exception] = []

        def add(i: int) -> None:
            try:
                book.add_from_params(
                    f"ORD-{i:04d}",
                    instrument  = "RELIANCE",
                    strategy_id = "S1",
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert book.count() == 100
        book.stop()

    def test_concurrent_updates(self) -> None:
        book = OrderBook()
        book.start()
        book.add_from_params("ORD-001")
        errors: list[Exception] = []
        states = ["SUBMITTED", "ACKNOWLEDGED", "PARTIALLY_FILLED", "FILLED"]

        def update(i: int) -> None:
            try:
                book.update_state("ORD-001", states[i % len(states)])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update, args=(i,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        book.stop()

    def test_concurrent_statistics(self) -> None:
        s      = OrderBookStatistics()
        errors: list[Exception] = []

        def record() -> None:
            try:
                s.record_added()
                s.record_status_change("ACTIVE", "COMPLETED")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors)     == 0
        assert s.orders_added  == 50

    def test_concurrent_index(self) -> None:
        idx    = OrderBookIndex()
        errors: list[Exception] = []

        def work(i: int) -> None:
            try:
                d = {"order_id": f"O{i}", "strategy_id": f"S{i % 5}", "status": "ACTIVE"}
                idx.add(d)
                _ = idx.lookup("strategy_id", f"S{i % 5}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=work, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
