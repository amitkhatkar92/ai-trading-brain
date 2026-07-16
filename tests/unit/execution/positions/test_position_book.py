"""tests/unit/execution/positions/test_position_book.py
==================================================
Test suite for C6 Phase 3 M3 — IIOS Position Book.

Coverage targets (95%+):
  * Constants, enums: BookEventType, IndexType, BookOperationType, ValidationSeverity
  * Exceptions — hierarchy, error codes, fields
  * BookEntry — delegates, touch, to_dict
  * PositionIndex — add, remove, reindex_state, all 11 lookups, utilization
  * FilterChain + built-in predicates
  * BookStatistics — all counters, properties, serialisation
  * BookEvent + 6 factory functions
  * BookEntrySnapshot / PositionBookSnapshot / FilteredSnapshot / HistoricalSnapshot
  * BookHistory — append, filters, eviction
  * SnapshotHistory — append, latest, get_by_id, eviction
  * BookQuery — is_single_lookup, is_index_query, is_empty
  * QueryResult — count, positions, to_dict
  * BookContext / make_book_context
  * BookValidator — all 4 checks, raise_if_invalid
  * BookFactory — create, validation failures
  * BookRegistry — lifecycle guard, add, remove, notify_state_changed, filters
  * PositionBook — all public operations, events, statistics, snapshots,
      validation, history, concurrency, regression guards

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from typing import List

import pytest

from iios.execution.positions.lifecycle import (
    Position,
    PositionDirection,
    PositionFactory,
    PositionProduct,
    PositionState,
)

from iios.execution.positions.book import (
    # constants
    BOOK_SYSTEM_ID,
    BookEventType,
    BookOperationType,
    IndexType,
    ValidationSeverity,
    VERSION,
    # exceptions
    BookEntryNotFoundError,
    DuplicateBookEntryError,
    PositionBookCapacityError,
    PositionBookError,
    PositionBookIndexError,
    PositionBookNotRunningError,
    PositionBookQueryError,
    PositionBookValidationError,
    # value types
    BookContext, make_book_context,
    BookEntry,
    BookEvent,
    make_position_added_event, make_position_updated_event,
    make_position_removed_event,
    make_snapshot_created_event, make_snapshot_published_event,
    make_book_validated_event,
    BookHistory, SnapshotHistory,
    BookEntrySnapshot, PositionBookSnapshot, FilteredSnapshot, HistoricalSnapshot,
    make_book_snapshot, make_filtered_snapshot, make_historical_snapshot,
    BookStatistics,
    BookValidationResult, ValidationFinding, BookValidator,
    FilterChain, PositionPredicate,
    active_filter, closed_filter, archived_filter, state_filter,
    instrument_filter, exchange_filter, portfolio_filter,
    strategy_filter, direction_filter, product_filter,
    min_quantity_filter, max_quantity_filter,
    long_filter, short_filter,
    BookQuery, QueryResult, make_query_result,
    PositionIndex,
    BookFactory,
    BookRegistry,
    PositionBook,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_position(
    instrument:   str = "NIFTY50",
    quantity:     Decimal = Decimal("100"),
    direction:    PositionDirection = PositionDirection.LONG,
    portfolio_id: str = "port-1",
    strategy_id:  str = "strat-1",
    decision_id:  str = "dec-1",
    workflow_id:  str = "wf-1",
    execution_id: str = "exec-1",
    product:      PositionProduct = PositionProduct.FUTURES,
    exchange:     str = "NSE",
) -> Position:
    f = PositionFactory()
    p = f.create(
        instrument=instrument,
        exchange=exchange,
        product=product,
        direction=direction,
        quantity=quantity,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        decision_id=decision_id,
        workflow_id=workflow_id,
        execution_id=execution_id,
    )
    return p


def _started_book(**kwargs) -> PositionBook:
    b = PositionBook(**kwargs)
    b.start()
    return b


def _add_open_position(book: PositionBook, **kwargs) -> BookEntry:
    pos = _make_position(**kwargs)
    pos.transition_to(PositionState.OPENING)
    pos.transition_to(PositionState.OPEN)
    return book.add(pos)


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_all_book_event_types(self):
        values = {e.value for e in BookEventType}
        for v in ("POSITION_ADDED", "POSITION_UPDATED", "POSITION_REMOVED",
                  "SNAPSHOT_CREATED", "SNAPSHOT_PUBLISHED", "BOOK_VALIDATED"):
            assert v in values

    def test_all_index_types(self):
        assert len(list(IndexType)) == 11

    def test_all_book_operation_types(self):
        values = {e.value for e in BookOperationType}
        for v in ("ADD", "UPDATE", "REMOVE", "QUERY", "SNAPSHOT", "VALIDATE"):
            assert v in values

    def test_validation_severity_levels(self):
        values = {e.value for e in ValidationSeverity}
        assert "ERROR" in values
        assert "WARNING" in values

    def test_version_string(self):
        assert VERSION == "1.0.0"

    def test_book_system_id(self):
        assert BOOK_SYSTEM_ID.startswith("iios:")


# ══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_all_inherit_book_error(self):
        for exc_cls in (
            PositionBookNotRunningError,
            BookEntryNotFoundError,
            DuplicateBookEntryError,
            PositionBookValidationError,
            PositionBookCapacityError,
            PositionBookIndexError,
            PositionBookQueryError,
        ):
            assert issubclass(exc_cls, PositionBookError)

    def test_not_running_code(self):
        e = PositionBookNotRunningError()
        assert "PB3-001" in str(e.code)

    def test_entry_not_found_code(self):
        e = BookEntryNotFoundError("pos-1")
        assert "PB3-002" in str(e.code)
        assert e.position_id == "pos-1"

    def test_duplicate_code(self):
        e = DuplicateBookEntryError("pos-2")
        assert "PB3-003" in str(e.code)
        assert e.position_id == "pos-2"

    def test_validation_error_has_errors(self):
        e = PositionBookValidationError("fail", errors=("e1", "e2"))
        assert "e1" in e.errors

    def test_capacity_error_stores_capacity(self):
        e = PositionBookCapacityError(5_000)
        assert e.capacity == 5_000
        assert "PB3-005" in str(e.code)

    def test_index_error_stores_index_type(self):
        e = PositionBookIndexError("dup", index_type=IndexType.POSITION_ID)
        assert e.index_type == IndexType.POSITION_ID
        assert "PB3-006" in str(e.code)

    def test_query_error_code(self):
        e = PositionBookQueryError("bad limit")
        assert "PB3-008" in str(e.code)


# ══════════════════════════════════════════════════════════════════════════════
# BookEntry
# ══════════════════════════════════════════════════════════════════════════════

class TestBookEntry:
    def test_entry_wraps_position(self):
        pos   = _make_position()
        entry = BookEntry(pos)
        assert entry.position is pos

    def test_entry_has_uuid(self):
        entry = BookEntry(_make_position())
        assert uuid.UUID(entry.entry_id)

    def test_delegates_instrument(self):
        entry = BookEntry(_make_position(instrument="BANKNIFTY"))
        assert entry.instrument == "BANKNIFTY"

    def test_delegates_portfolio_id(self):
        entry = BookEntry(_make_position(portfolio_id="my-port"))
        assert entry.portfolio_id == "my-port"

    def test_delegates_state(self):
        pos = _make_position()
        entry = BookEntry(pos)
        assert entry.state == PositionState.CREATED

    def test_touch_updates_last_seen(self):
        entry = BookEntry(_make_position())
        old = entry.last_seen_at
        time.sleep(0.01)
        entry.touch()
        assert entry.last_seen_at > old

    def test_to_dict_has_expected_keys(self):
        d = BookEntry(_make_position()).to_dict()
        for k in ("entry_id", "position_id", "instrument", "exchange",
                  "product", "direction", "state", "portfolio_id",
                  "strategy_id", "added_at", "added_by"):
            assert k in d

    def test_repr(self):
        entry = BookEntry(_make_position())
        r = repr(entry)
        assert "BookEntry" in r
        assert "CREATED" in r


# ══════════════════════════════════════════════════════════════════════════════
# PositionIndex
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionIndex:
    def _entry(self, **kwargs) -> BookEntry:
        return BookEntry(_make_position(**kwargs))

    def test_add_and_get(self):
        idx = PositionIndex()
        e   = self._entry()
        idx.add(e)
        assert idx.get(e.position_id) is e

    def test_duplicate_raises(self):
        idx = PositionIndex()
        e   = self._entry()
        idx.add(e)
        with pytest.raises(PositionBookIndexError):
            idx.add(e)

    def test_remove(self):
        idx = PositionIndex()
        e   = self._entry()
        idx.add(e)
        idx.remove(e)
        assert idx.get(e.position_id) is None

    def test_remove_idempotent(self):
        idx = PositionIndex()
        e   = self._entry()
        idx.remove(e)   # should not raise

    def test_contains(self):
        idx = PositionIndex()
        e   = self._entry()
        idx.add(e)
        assert idx.contains(e.position_id) is True
        assert idx.contains("ghost")        is False

    def test_count(self):
        idx = PositionIndex()
        idx.add(self._entry())
        idx.add(self._entry())
        assert idx.count() == 2

    def test_all(self):
        idx = PositionIndex()
        e1 = self._entry()
        e2 = self._entry()
        idx.add(e1)
        idx.add(e2)
        assert len(idx.all()) == 2

    def test_by_portfolio(self):
        idx = PositionIndex()
        idx.add(self._entry(portfolio_id="A"))
        idx.add(self._entry(portfolio_id="B"))
        assert len(idx.by_portfolio("A")) == 1

    def test_by_strategy(self):
        idx = PositionIndex()
        idx.add(self._entry(strategy_id="s1"))
        idx.add(self._entry(strategy_id="s2"))
        assert len(idx.by_strategy("s1")) == 1

    def test_by_decision(self):
        idx = PositionIndex()
        idx.add(self._entry(decision_id="d1"))
        assert len(idx.by_decision("d1")) == 1
        assert len(idx.by_decision("ghost")) == 0

    def test_by_execution(self):
        idx = PositionIndex()
        idx.add(self._entry(execution_id="ex1"))
        assert len(idx.by_execution("ex1")) == 1

    def test_by_workflow(self):
        idx = PositionIndex()
        idx.add(self._entry(workflow_id="wf-A"))
        assert len(idx.by_workflow("wf-A")) == 1

    def test_by_instrument(self):
        idx = PositionIndex()
        idx.add(self._entry(instrument="NIFTY50"))
        idx.add(self._entry(instrument="BANKNIFTY"))
        assert len(idx.by_instrument("NIFTY50")) == 1

    def test_by_exchange(self):
        idx = PositionIndex()
        idx.add(self._entry(exchange="NSE"))
        assert len(idx.by_exchange("NSE")) == 1

    def test_by_product(self):
        idx = PositionIndex()
        idx.add(self._entry(product=PositionProduct.FUTURES))
        idx.add(self._entry(product=PositionProduct.OPTIONS))
        assert len(idx.by_product("FUTURES")) == 1

    def test_by_direction(self):
        idx = PositionIndex()
        idx.add(self._entry(direction=PositionDirection.LONG))
        idx.add(self._entry(direction=PositionDirection.SHORT))
        assert len(idx.by_direction("LONG")) == 1

    def test_by_state_after_reindex(self):
        idx  = PositionIndex()
        pos  = _make_position()
        e    = BookEntry(pos)
        idx.add(e)
        # CREATED state — not in active
        assert len(idx.active()) == 0

        # Transition to OPENING
        pos.transition_to(PositionState.OPENING)
        idx.reindex_state(e, PositionState.CREATED)
        assert len(idx.active()) == 1

    def test_active(self):
        idx = PositionIndex()
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        e = BookEntry(pos)
        idx.add(e)
        assert len(idx.active()) == 1

    def test_closed(self):
        idx = PositionIndex()
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED):
            pos.transition_to(s)
        e = BookEntry(pos)
        idx.add(e)
        assert len(idx.closed()) == 1
        assert len(idx.archived()) == 0

    def test_archived(self):
        idx = PositionIndex()
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        e = BookEntry(pos)
        idx.add(e)
        assert len(idx.archived()) == 1

    def test_utilization_increments(self):
        idx = PositionIndex()
        e   = self._entry()
        idx.add(e)
        idx.get(e.position_id)
        util = idx.utilization()
        assert util[IndexType.POSITION_ID] >= 1

    def test_reset_utilization(self):
        idx = PositionIndex()
        e   = self._entry()
        idx.add(e)
        idx.get(e.position_id)
        idx.reset_utilization()
        assert idx.utilization()[IndexType.POSITION_ID] == 0


# ══════════════════════════════════════════════════════════════════════════════
# Filters
# ══════════════════════════════════════════════════════════════════════════════

class TestFilters:
    def _pos(self, **kwargs) -> Position:
        return _make_position(**kwargs)

    def test_active_filter(self):
        pos = self._pos()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        assert active_filter()(pos) is True

    def test_closed_filter(self):
        pos = self._pos()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED):
            pos.transition_to(s)
        assert closed_filter()(pos) is True
        assert active_filter()(pos) is False

    def test_archived_filter(self):
        pos = self._pos()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        assert archived_filter()(pos) is True
        assert closed_filter()(pos)   is False

    def test_state_filter_exact(self):
        pos = self._pos()
        assert state_filter(PositionState.CREATED)(pos) is True
        assert state_filter(PositionState.OPEN)(pos)    is False

    def test_instrument_filter(self):
        pos = self._pos(instrument="NIFTY50")
        assert instrument_filter("NIFTY50")(pos)   is True
        assert instrument_filter("BANKNIFTY")(pos) is False

    def test_exchange_filter(self):
        pos = self._pos(exchange="NSE")
        assert exchange_filter("NSE")(pos) is True
        assert exchange_filter("BSE")(pos) is False

    def test_portfolio_filter(self):
        pos = self._pos(portfolio_id="port-A")
        assert portfolio_filter("port-A")(pos) is True
        assert portfolio_filter("port-B")(pos) is False

    def test_strategy_filter(self):
        pos = self._pos(strategy_id="s1")
        assert strategy_filter("s1")(pos) is True
        assert strategy_filter("s2")(pos) is False

    def test_direction_filter(self):
        pos = self._pos(direction=PositionDirection.LONG)
        assert direction_filter(PositionDirection.LONG)(pos)  is True
        assert direction_filter(PositionDirection.SHORT)(pos) is False

    def test_product_filter(self):
        pos = self._pos(product=PositionProduct.FUTURES)
        assert product_filter(PositionProduct.FUTURES)(pos) is True
        assert product_filter(PositionProduct.OPTIONS)(pos) is False

    def test_min_quantity_filter(self):
        pos = self._pos(quantity=Decimal("100"))
        assert min_quantity_filter(Decimal("100"))(pos) is True
        assert min_quantity_filter(Decimal("101"))(pos) is False

    def test_max_quantity_filter(self):
        pos = self._pos(quantity=Decimal("100"))
        assert max_quantity_filter(Decimal("100"))(pos) is True
        assert max_quantity_filter(Decimal("99"))(pos)  is False

    def test_long_filter(self):
        pos = self._pos(direction=PositionDirection.LONG)
        assert long_filter()(pos)  is True
        assert short_filter()(pos) is False

    def test_filter_chain_and(self):
        pos = self._pos(instrument="NIFTY50", exchange="NSE")
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        chain = FilterChain(active_filter(), instrument_filter("NIFTY50"))
        assert chain.matches(pos) is True
        chain2 = FilterChain(active_filter(), instrument_filter("BANKNIFTY"))
        assert chain2.matches(pos) is False

    def test_filter_chain_apply(self):
        positions = [
            self._pos(instrument="NIFTY50"),
            self._pos(instrument="BANKNIFTY"),
        ]
        chain  = FilterChain(instrument_filter("NIFTY50"))
        result = chain.apply(positions)
        assert len(result) == 1

    def test_filter_chain_any_of(self):
        pos = self._pos(instrument="NIFTY50")
        pred = FilterChain.any_of(
            instrument_filter("NIFTY50"),
            instrument_filter("BANKNIFTY"),
        )
        assert pred(pos) is True

    def test_filter_chain_none_of(self):
        pos  = self._pos(instrument="NIFTY50")
        pred = FilterChain.none_of(instrument_filter("BANKNIFTY"))
        assert pred(pos) is True

    def test_filter_chain_negate(self):
        pos  = self._pos(instrument="NIFTY50")
        pred = FilterChain.negate(instrument_filter("NIFTY50"))
        assert pred(pos) is False

    def test_filter_chain_len(self):
        chain = FilterChain(active_filter(), closed_filter())
        assert len(chain) == 2


# ══════════════════════════════════════════════════════════════════════════════
# BookStatistics
# ══════════════════════════════════════════════════════════════════════════════

class TestBookStatistics:
    def test_initial_zero(self):
        s = BookStatistics()
        assert s.positions_added   == 0
        assert s.total_queries     == 0
        assert s.total_snapshots   == 0

    def test_record_added(self):
        s = BookStatistics()
        s.record_added()
        assert s.positions_added == 1
        assert s.positions_in_book == 1

    def test_record_removed(self):
        s = BookStatistics()
        s.record_added()
        s.record_removed()
        assert s.positions_removed == 1
        assert s.positions_in_book == 0

    def test_record_query(self):
        s = BookStatistics()
        s.record_query(elapsed_ms=10.0)
        s.record_query(elapsed_ms=20.0)
        assert s.total_queries == 2
        assert s.average_lookup_time_ms == pytest.approx(15.0)

    def test_record_snapshot(self):
        s = BookStatistics()
        s.record_snapshot()
        assert s.snapshot_count == 1

    def test_failed_query(self):
        s = BookStatistics()
        s.record_failed_query()
        assert s.failed_queries == 1
        assert s.total_queries  == 1

    def test_average_lookup_with_failures(self):
        s = BookStatistics()
        s.record_query(10.0)
        s.record_failed_query()  # not counted in timing average
        assert s.average_lookup_time_ms == pytest.approx(10.0)

    def test_update_live_counts(self):
        s = BookStatistics()
        s.update_live_counts(active=5, closed=3, archived=2, suspended=1)
        assert s.active_positions    == 5
        assert s.closed_positions    == 3
        assert s.archived_positions  == 2
        assert s.suspended_positions == 1

    def test_update_index_utilization(self):
        s = BookStatistics()
        util = {IndexType.PORTFOLIO_ID: 10, IndexType.INSTRUMENT: 5}
        s.update_index_utilization(util)
        assert s.index_utilization["PORTFOLIO_ID"] == 10

    def test_to_dict_keys(self):
        d = BookStatistics().to_dict()
        for k in ("positions_added", "positions_removed", "total_queries",
                  "total_snapshots", "average_lookup_time_ms", "index_utilization"):
            assert k in d

    def test_query_count_alias(self):
        s = BookStatistics()
        s.record_query(5.0)
        assert s.query_count == s.total_queries


# ══════════════════════════════════════════════════════════════════════════════
# BookEvents
# ══════════════════════════════════════════════════════════════════════════════

class TestBookEvents:
    def _check(self, event: BookEvent, expected: BookEventType):
        assert event.event_type == expected
        assert uuid.UUID(event.event_id)
        assert event.occurred_at > 0

    def test_make_position_added_event(self):
        e = make_position_added_event("p1", portfolio_id="port")
        self._check(e, BookEventType.POSITION_ADDED)
        assert e.position_id == "p1"

    def test_make_position_updated_event(self):
        self._check(make_position_updated_event("p"), BookEventType.POSITION_UPDATED)

    def test_make_position_removed_event(self):
        self._check(make_position_removed_event("p"), BookEventType.POSITION_REMOVED)

    def test_make_snapshot_created_event(self):
        self._check(make_snapshot_created_event(), BookEventType.SNAPSHOT_CREATED)

    def test_make_snapshot_published_event(self):
        self._check(make_snapshot_published_event(), BookEventType.SNAPSHOT_PUBLISHED)

    def test_make_book_validated_event(self):
        self._check(make_book_validated_event(), BookEventType.BOOK_VALIDATED)

    def test_to_dict_keys(self):
        e = make_position_added_event("p")
        d = e.to_dict()
        for k in ("event_id", "event_type", "position_id", "actor", "occurred_at"):
            assert k in d

    def test_all_six_event_types(self):
        assert len(list(BookEventType)) == 6


# ══════════════════════════════════════════════════════════════════════════════
# Snapshot types
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotTypes:
    def _entry(self) -> BookEntry:
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        return BookEntry(pos)

    def test_book_entry_snapshot_from_entry(self):
        e  = self._entry()
        es = BookEntrySnapshot.from_entry(e)
        assert es.position_id == e.position_id
        assert es.state       == "OPEN"
        assert es.instrument  == "NIFTY50"

    def test_book_entry_snapshot_to_dict(self):
        es = BookEntrySnapshot.from_entry(self._entry())
        d  = es.to_dict()
        for k in ("position_id", "entry_id", "state", "instrument",
                  "portfolio_id", "strategy_id"):
            assert k in d

    def test_make_book_snapshot_empty(self):
        snap = make_book_snapshot([], BookStatistics())
        assert snap.total_positions == 0
        assert snap.is_empty is True

    def test_make_book_snapshot_with_entries(self):
        e    = self._entry()
        snap = make_book_snapshot([e], BookStatistics())
        assert snap.total_positions == 1
        assert snap.active_count    == 1
        assert snap.entry_count     == 1

    def test_position_book_snapshot_to_dict(self):
        snap = make_book_snapshot([], BookStatistics())
        d    = snap.to_dict()
        for k in ("snapshot_id", "total_positions", "active_count",
                  "statistics", "taken_at", "version"):
            assert k in d

    def test_make_filtered_snapshot(self):
        e    = self._entry()
        snap = make_filtered_snapshot([e], "my-filter")
        assert snap.filter_label  == "my-filter"
        assert snap.total_matched == 1
        assert snap.is_empty      is False

    def test_filtered_snapshot_to_dict(self):
        snap = make_filtered_snapshot([], "test")
        d    = snap.to_dict()
        assert "filter_label" in d
        assert "total_matched" in d

    def test_make_historical_snapshot(self):
        book_snap = make_book_snapshot([], BookStatistics())
        hist      = make_historical_snapshot(book_snap)
        assert hist.snapshot is book_snap
        assert hist.taken_at == book_snap.taken_at
        assert hist.age_seconds >= 0

    def test_historical_snapshot_to_dict(self):
        hist = make_historical_snapshot(make_book_snapshot([], BookStatistics()))
        d    = hist.to_dict()
        for k in ("reference_id", "snapshot_id", "taken_at", "retrieved_at"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# BookHistory and SnapshotHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestBookHistory:
    def _evt(self, position_id: str = "p1") -> BookEvent:
        return make_position_added_event(position_id)

    def test_empty_on_init(self):
        h = BookHistory()
        assert len(h) == 0

    def test_append_and_all(self):
        h = BookHistory()
        e = self._evt()
        h.append(e)
        assert len(h) == 1
        assert h.all()[0] is e

    def test_latest(self):
        h = BookHistory()
        e1 = self._evt()
        e2 = self._evt()
        h.append(e1)
        h.append(e2)
        assert h.latest(1)[0] is e2

    def test_by_type(self):
        h = BookHistory()
        h.append(make_position_added_event("p1"))
        h.append(make_position_removed_event("p2"))
        assert len(h.by_type(BookEventType.POSITION_ADDED)) == 1

    def test_by_position(self):
        h = BookHistory()
        h.append(make_position_added_event("p1"))
        h.append(make_position_added_event("p2"))
        assert len(h.by_position("p1")) == 1

    def test_eviction(self):
        h = BookHistory(max_size=2)
        h.append(self._evt())
        h.append(self._evt())
        h.append(self._evt())
        assert len(h)    == 2
        assert h.evicted == 1
        assert h.total   == 3

    def test_iter(self):
        h = BookHistory()
        e = self._evt()
        h.append(e)
        assert list(h)[0] is e


class TestSnapshotHistory:
    def _snap(self) -> PositionBookSnapshot:
        return make_book_snapshot([], BookStatistics())

    def test_empty_latest_returns_none(self):
        h = SnapshotHistory()
        assert h.latest() is None

    def test_append_and_latest(self):
        h = SnapshotHistory()
        s = self._snap()
        h.append(s)
        latest = h.latest()
        assert latest is not None
        assert latest.snapshot is s

    def test_get_by_id(self):
        h = SnapshotHistory()
        s = self._snap()
        h.append(s)
        hist = h.get_by_id(s.snapshot_id)
        assert hist is not None
        assert hist.snapshot_id == s.snapshot_id

    def test_get_by_id_not_found(self):
        h = SnapshotHistory()
        assert h.get_by_id("ghost") is None

    def test_all_returns_historical_wrappers(self):
        h = SnapshotHistory()
        h.append(self._snap())
        h.append(self._snap())
        items = h.all()
        assert len(items) == 2
        assert all(isinstance(i, HistoricalSnapshot) for i in items)

    def test_eviction(self):
        h = SnapshotHistory(max_size=2)
        h.append(self._snap())
        h.append(self._snap())
        h.append(self._snap())
        assert len(h)    == 2
        assert h.evicted == 1

    def test_last_n(self):
        h = SnapshotHistory()
        for _ in range(5):
            h.append(self._snap())
        assert len(h.last_n(3)) == 3


# ══════════════════════════════════════════════════════════════════════════════
# BookQuery and QueryResult
# ══════════════════════════════════════════════════════════════════════════════

class TestBookQuery:
    def test_is_single_lookup_true(self):
        q = BookQuery(position_id="p1")
        assert q.is_single_lookup is True

    def test_is_single_lookup_false_with_extra_filter(self):
        q = BookQuery(position_id="p1", portfolio_id="port")
        assert q.is_single_lookup is False

    def test_is_empty_true(self):
        assert BookQuery().is_empty is True

    def test_is_empty_false(self):
        assert BookQuery(portfolio_id="p").is_empty is False

    def test_is_index_query_single_field(self):
        q = BookQuery(portfolio_id="port")
        assert q.is_index_query is True

    def test_is_index_query_false_with_custom_filter(self):
        q = BookQuery(portfolio_id="port", custom_filter=lambda p: True)
        assert q.is_index_query is False

    def test_is_index_query_false_multi_field(self):
        q = BookQuery(portfolio_id="port", strategy_id="s")
        assert q.is_index_query is False

    def test_default_limit(self):
        assert BookQuery().limit > 0


class TestQueryResult:
    def test_count_and_is_empty(self):
        r = make_query_result([], 1.0)
        assert r.count    == 0
        assert r.is_empty is True

    def test_positions_list(self):
        pos   = _make_position()
        entry = BookEntry(pos)
        r     = make_query_result([entry], 1.0)
        assert r.positions[0] is pos

    def test_to_dict_keys(self):
        r = make_query_result([], 1.0)
        d = r.to_dict()
        for k in ("query_id", "count", "elapsed_ms", "executed_at"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# BookContext
# ══════════════════════════════════════════════════════════════════════════════

class TestBookContext:
    def test_make_book_context_generates_uuid(self):
        ctx = make_book_context(BookOperationType.ADD, portfolio_id="p")
        assert uuid.UUID(ctx.context_id)
        assert ctx.portfolio_id == "p"

    def test_has_workflow_true(self):
        ctx = make_book_context(BookOperationType.QUERY, workflow_id="wf-1")
        assert ctx.has_workflow is True

    def test_has_workflow_false(self):
        ctx = make_book_context(BookOperationType.QUERY)
        assert ctx.has_workflow is False

    def test_has_execution(self):
        ctx = make_book_context(BookOperationType.ADD, execution_id="ex-1")
        assert ctx.has_execution is True

    def test_age_ms_positive(self):
        ctx = make_book_context(BookOperationType.ADD)
        time.sleep(0.01)
        assert ctx.age_ms > 0

    def test_to_dict_keys(self):
        d = make_book_context(BookOperationType.ADD).to_dict()
        for k in ("context_id", "operation_type", "portfolio_id", "requester"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# BookValidator
# ══════════════════════════════════════════════════════════════════════════════

class TestBookValidator:
    def _fresh_registry(self) -> BookRegistry:
        r = BookRegistry()
        r.start()
        return r

    def test_empty_book_is_valid(self):
        reg = self._fresh_registry()
        v   = BookValidator()
        res = v.validate_all(reg)
        assert res.is_valid is True
        assert res.error_count == 0

    def test_valid_book_with_positions(self):
        reg = self._fresh_registry()
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        entry = BookEntry(pos)
        reg.add(entry)
        v   = BookValidator()
        res = v.validate_all(reg)
        assert res.is_valid is True

    def test_identifier_warning_empty_portfolio(self):
        reg   = self._fresh_registry()
        # Manually create a position with empty portfolio_id
        f   = PositionFactory()
        pos = f.create(
            instrument="NIFTY50", exchange="NSE",
            product=PositionProduct.FUTURES,
            direction=PositionDirection.LONG,
            quantity=Decimal("100"),
            portfolio_id="",  # empty
            strategy_id="s1",
        )
        entry = BookEntry(pos)
        reg.add(entry)
        v   = BookValidator()
        res = v.validate_all(reg)
        # Should produce a WARNING (not error) for empty portfolio_id
        assert res.warning_count > 0

    def test_validate_no_duplicates_clean(self):
        reg = self._fresh_registry()
        v   = BookValidator()
        findings = v.validate_no_duplicates(reg)
        assert findings == []

    def test_validate_index_consistency_clean(self):
        reg = self._fresh_registry()
        entry = BookEntry(_make_position())
        reg.add(entry)
        v  = BookValidator()
        findings = v.validate_index_consistency(reg)
        assert findings == []

    def test_validate_lifecycle_consistency_clean(self):
        reg = self._fresh_registry()
        v   = BookValidator()
        findings = v.validate_lifecycle_consistency(reg)
        assert findings == []

    def test_raise_if_invalid_raises(self):
        finding = ValidationFinding(
            severity=ValidationSeverity.ERROR,
            code="PB3-X",
            message="test error",
        )
        result = BookValidationResult(
            is_valid=False,
            findings=(finding,),
        )
        v = BookValidator()
        with pytest.raises(PositionBookValidationError):
            v.raise_if_invalid(result)

    def test_raise_if_invalid_passes(self):
        result = BookValidationResult(is_valid=True, findings=())
        v = BookValidator()
        v.raise_if_invalid(result)  # must not raise

    def test_validation_finding_to_dict(self):
        f = ValidationFinding(ValidationSeverity.ERROR, "PB3-X", "msg")
        d = f.to_dict()
        assert d["severity"] == "ERROR"
        assert d["code"]     == "PB3-X"


# ══════════════════════════════════════════════════════════════════════════════
# BookFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestBookFactory:
    def test_create_returns_entry(self):
        f   = BookFactory()
        pos = _make_position()
        e   = f.create(pos)
        assert isinstance(e, BookEntry)
        assert e.position is pos

    def test_create_empty_instrument_raises(self):
        f   = BookFactory()
        pos = _make_position()
        pos._instrument = ""  # directly corrupt
        with pytest.raises(PositionBookValidationError):
            f.create(pos)

    def test_create_none_product_raises(self):
        f   = BookFactory()
        pos = _make_position()
        pos._product = None  # type: ignore[assignment]
        with pytest.raises(PositionBookValidationError):
            f.create(pos)

    def test_create_zero_quantity_raises(self):
        f   = BookFactory()
        pos = _make_position(quantity=Decimal("100"))
        pos._quantity = Decimal("0")  # type: ignore[assignment]
        with pytest.raises(PositionBookValidationError):
            f.create(pos)

    def test_create_empty_exchange_raises(self):
        f   = BookFactory()
        pos = _make_position()
        pos._exchange = ""
        with pytest.raises(PositionBookValidationError):
            f.create(pos)


# ══════════════════════════════════════════════════════════════════════════════
# BookRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestBookRegistry:
    def _reg(self) -> BookRegistry:
        r = BookRegistry()
        r.start()
        return r

    def _entry(self) -> BookEntry:
        return BookEntry(_make_position())

    def test_add_before_start_raises(self):
        reg = BookRegistry()
        with pytest.raises(PositionBookNotRunningError):
            reg.add(self._entry())

    def test_add_after_start(self):
        reg = self._reg()
        reg.add(self._entry())
        assert reg.count == 1

    def test_duplicate_add_raises(self):
        reg = self._reg()
        e   = self._entry()
        reg.add(e)
        with pytest.raises(DuplicateBookEntryError):
            reg.add(e)

    def test_capacity_error(self):
        reg = BookRegistry(max_positions=1)
        reg.start()
        reg.add(self._entry())
        with pytest.raises(PositionBookCapacityError):
            reg.add(self._entry())

    def test_remove_returns_entry(self):
        reg = self._reg()
        e   = self._entry()
        reg.add(e)
        removed = reg.remove(e.position_id)
        assert removed.position_id == e.position_id
        assert reg.count           == 0

    def test_remove_not_found_raises(self):
        reg = self._reg()
        with pytest.raises(BookEntryNotFoundError):
            reg.remove("ghost")

    def test_get_returns_entry(self):
        reg = self._reg()
        e   = self._entry()
        reg.add(e)
        assert reg.get(e.position_id) is e

    def test_get_none_for_unknown(self):
        reg = self._reg()
        assert reg.get("ghost") is None

    def test_require_raises_for_unknown(self):
        reg = self._reg()
        with pytest.raises(BookEntryNotFoundError):
            reg.require("ghost")

    def test_contains(self):
        reg = self._reg()
        e   = self._entry()
        reg.add(e)
        assert reg.contains(e.position_id) is True

    def test_is_empty(self):
        reg = self._reg()
        assert reg.is_empty is True
        reg.add(self._entry())
        assert reg.is_empty is False

    def test_all(self):
        reg = self._reg()
        reg.add(self._entry())
        reg.add(self._entry())
        assert len(reg.all()) == 2

    def test_notify_state_changed_updates_index(self):
        reg = self._reg()
        pos = _make_position()
        e   = BookEntry(pos)
        reg.add(e)
        # Transition to OPENING
        pos.transition_to(PositionState.OPENING)
        reg.notify_state_changed(e, PositionState.CREATED)
        assert len(reg.active()) == 1

    def test_by_portfolio(self):
        reg = self._reg()
        reg.add(BookEntry(_make_position(portfolio_id="A")))
        reg.add(BookEntry(_make_position(portfolio_id="B")))
        assert len(reg.by_portfolio("A")) == 1

    def test_active(self):
        reg = self._reg()
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        reg.add(BookEntry(pos))
        assert len(reg.active()) == 1

    def test_closed(self):
        reg = self._reg()
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED):
            pos.transition_to(s)
        reg.add(BookEntry(pos))
        assert len(reg.closed()) == 1

    def test_archived(self):
        reg = self._reg()
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        reg.add(BookEntry(pos))
        assert len(reg.archived()) == 1

    def test_index_property(self):
        reg = self._reg()
        assert isinstance(reg.index, PositionIndex)


# ══════════════════════════════════════════════════════════════════════════════
# PositionBook — main facade
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionBook:
    # ── lifecycle ─────────────────────────────────────────────────────────────

    def test_running_after_start(self):
        b = _started_book()
        assert b.lifecycle_state().value == "running"
        b.stop()

    def test_operations_raise_before_start(self):
        b = PositionBook()
        with pytest.raises(PositionBookNotRunningError):
            b.add(_make_position())

    def test_stopped_after_stop(self):
        b = _started_book()
        b.stop()
        assert b.lifecycle_state().value != "running"

    # ── add ───────────────────────────────────────────────────────────────────

    def test_add_position(self):
        b = _started_book()
        e = b.add(_make_position())
        assert isinstance(e, BookEntry)
        assert b.position_count == 1
        b.stop()

    def test_add_duplicate_raises(self):
        b   = _started_book()
        pos = _make_position()
        b.add(pos)
        with pytest.raises(DuplicateBookEntryError):
            b.add(pos)
        b.stop()

    def test_add_invalid_position_raises(self):
        b   = _started_book()
        pos = _make_position()
        pos._instrument = ""
        with pytest.raises(PositionBookValidationError):
            b.add(pos)
        b.stop()

    def test_add_emits_event(self):
        b = _started_book()
        b.add(_make_position())
        evts = [e for e in b.events() if e.event_type == BookEventType.POSITION_ADDED]
        assert len(evts) == 1
        b.stop()

    def test_add_increments_statistics(self):
        b = _started_book()
        b.add(_make_position())
        assert b.statistics().positions_added == 1
        b.stop()

    # ── update ────────────────────────────────────────────────────────────────

    def test_update_touches_entry(self):
        b   = _started_book()
        pos = _make_position()
        e   = b.add(pos)
        old = e.last_seen_at
        time.sleep(0.01)
        b.update(e.position_id)
        assert e.last_seen_at > old
        b.stop()

    def test_update_not_found_raises(self):
        b = _started_book()
        with pytest.raises(BookEntryNotFoundError):
            b.update("ghost")
        b.stop()

    def test_update_emits_event(self):
        b   = _started_book()
        pos = _make_position()
        e   = b.add(pos)
        b.update(e.position_id)
        evts = [ev for ev in b.events() if ev.event_type == BookEventType.POSITION_UPDATED]
        assert len(evts) >= 1
        b.stop()

    # ── remove ────────────────────────────────────────────────────────────────

    def test_remove_position(self):
        b = _started_book()
        e = b.add(_make_position())
        b.remove(e.position_id)
        assert b.position_count == 0
        b.stop()

    def test_remove_not_found_raises(self):
        b = _started_book()
        with pytest.raises(BookEntryNotFoundError):
            b.remove("ghost")
        b.stop()

    def test_remove_emits_event(self):
        b = _started_book()
        e = b.add(_make_position())
        b.remove(e.position_id)
        evts = [ev for ev in b.events() if ev.event_type == BookEventType.POSITION_REMOVED]
        assert len(evts) == 1
        b.stop()

    def test_remove_decrements_statistics(self):
        b = _started_book()
        e = b.add(_make_position())
        b.remove(e.position_id)
        s = b.statistics()
        assert s.positions_removed == 1
        b.stop()

    # ── notify_state_changed ──────────────────────────────────────────────────

    def test_notify_state_changed(self):
        b   = _started_book()
        pos = _make_position()
        e   = b.add(pos)
        pos.transition_to(PositionState.OPENING)
        b.notify_state_changed(e.position_id, PositionState.CREATED)
        assert len(b.find_active()) == 1
        b.stop()

    def test_notify_state_changed_not_found_raises(self):
        b = _started_book()
        with pytest.raises(BookEntryNotFoundError):
            b.notify_state_changed("ghost", PositionState.CREATED)
        b.stop()

    def test_notify_state_changed_emits_event(self):
        b   = _started_book()
        pos = _make_position()
        e   = b.add(pos)
        pos.transition_to(PositionState.OPENING)
        b.notify_state_changed(e.position_id, PositionState.CREATED)
        evts = [ev for ev in b.events()
                if ev.event_type == BookEventType.POSITION_UPDATED]
        assert len(evts) >= 1
        b.stop()

    # ── find (structured query) ───────────────────────────────────────────────

    def test_find_single_lookup(self):
        b   = _started_book()
        e   = b.add(_make_position())
        res = b.find(BookQuery(position_id=e.position_id))
        assert res.count == 1
        assert res.entries[0].position_id == e.position_id
        b.stop()

    def test_find_by_portfolio(self):
        b = _started_book()
        b.add(_make_position(portfolio_id="A"))
        b.add(_make_position(portfolio_id="B"))
        res = b.find(BookQuery(portfolio_id="A"))
        assert res.count == 1
        b.stop()

    def test_find_by_strategy(self):
        b = _started_book()
        b.add(_make_position(strategy_id="s1"))
        b.add(_make_position(strategy_id="s2"))
        res = b.find(BookQuery(strategy_id="s1"))
        assert res.count == 1
        b.stop()

    def test_find_by_decision(self):
        b = _started_book()
        b.add(_make_position(decision_id="d1"))
        res = b.find(BookQuery(decision_id="d1"))
        assert res.count == 1
        b.stop()

    def test_find_by_execution(self):
        b = _started_book()
        b.add(_make_position(execution_id="ex1"))
        res = b.find(BookQuery(execution_id="ex1"))
        assert res.count == 1
        b.stop()

    def test_find_by_workflow(self):
        b = _started_book()
        b.add(_make_position(workflow_id="wf1"))
        res = b.find(BookQuery(workflow_id="wf1"))
        assert res.count == 1
        b.stop()

    def test_find_by_instrument(self):
        b = _started_book()
        b.add(_make_position(instrument="NIFTY50"))
        b.add(_make_position(instrument="BANKNIFTY"))
        res = b.find(BookQuery(instrument="NIFTY50"))
        assert res.count == 1
        b.stop()

    def test_find_by_exchange(self):
        b = _started_book()
        b.add(_make_position(exchange="NSE"))
        res = b.find(BookQuery(exchange="NSE"))
        assert res.count >= 1
        b.stop()

    def test_find_by_product(self):
        b = _started_book()
        b.add(_make_position(product=PositionProduct.FUTURES))
        b.add(_make_position(product=PositionProduct.OPTIONS))
        res = b.find(BookQuery(product=PositionProduct.FUTURES))
        assert res.count == 1
        b.stop()

    def test_find_by_direction(self):
        b = _started_book()
        b.add(_make_position(direction=PositionDirection.LONG))
        b.add(_make_position(direction=PositionDirection.SHORT))
        res = b.find(BookQuery(direction=PositionDirection.LONG))
        assert res.count == 1
        b.stop()

    def test_find_by_state(self):
        b   = _started_book()
        _add_open_position(b)
        res = b.find(BookQuery(state=PositionState.OPEN))
        assert res.count == 1
        b.stop()

    def test_find_all_empty_query(self):
        b = _started_book()
        b.add(_make_position())
        b.add(_make_position())
        res = b.find(BookQuery())
        assert res.count == 2
        b.stop()

    def test_find_with_custom_filter(self):
        b = _started_book()
        b.add(_make_position(instrument="NIFTY50"))
        b.add(_make_position(instrument="BANKNIFTY"))
        res = b.find(BookQuery(
            custom_filter=lambda p: p.instrument == "NIFTY50"
        ))
        assert res.count == 1
        b.stop()

    def test_find_respects_limit(self):
        b = _started_book()
        for _ in range(5):
            b.add(_make_position())
        res = b.find(BookQuery(limit=2))
        assert res.count == 2
        b.stop()

    def test_find_invalid_limit_raises(self):
        b = _started_book()
        with pytest.raises(PositionBookQueryError):
            b.find(BookQuery(limit=0))
        b.stop()

    def test_find_not_found_returns_empty(self):
        b   = _started_book()
        res = b.find(BookQuery(position_id="ghost"))
        assert res.count == 0
        b.stop()

    def test_find_increments_query_statistics(self):
        b = _started_book()
        b.find(BookQuery())
        assert b.statistics().total_queries == 1
        b.stop()

    # ── filter ────────────────────────────────────────────────────────────────

    def test_filter_custom_predicate(self):
        b = _started_book()
        b.add(_make_position(instrument="NIFTY50"))
        b.add(_make_position(instrument="BANKNIFTY"))
        res = b.filter(instrument_filter("NIFTY50"))
        assert res.count == 1
        b.stop()

    # ── convenience lookups ───────────────────────────────────────────────────

    def test_find_by_id(self):
        b   = _started_book()
        e   = b.add(_make_position())
        found = b.find_by_id(e.position_id)
        assert found is e
        b.stop()

    def test_find_by_id_none(self):
        b = _started_book()
        assert b.find_by_id("ghost") is None
        b.stop()

    def test_require_by_id_raises(self):
        b = _started_book()
        with pytest.raises(BookEntryNotFoundError):
            b.require_by_id("ghost")
        b.stop()

    def test_find_active(self):
        b   = _started_book()
        _add_open_position(b)
        b.add(_make_position())  # CREATED, not active
        assert len(b.find_active()) == 1
        b.stop()

    def test_find_closed(self):
        b   = _started_book()
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED):
            pos.transition_to(s)
        b.add(pos)
        assert len(b.find_closed()) == 1
        b.stop()

    def test_find_archived(self):
        b   = _started_book()
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        b.add(pos)
        assert len(b.find_archived()) == 1
        b.stop()

    def test_find_suspended(self):
        b   = _started_book()
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        pos.transition_to(PositionState.SUSPENDED)
        b.add(pos)
        assert len(b.find_suspended()) == 1
        b.stop()

    # ── snapshot ──────────────────────────────────────────────────────────────

    def test_snapshot_returns_book_snapshot(self):
        b    = _started_book()
        _add_open_position(b)
        snap = b.snapshot()
        assert isinstance(snap, PositionBookSnapshot)
        assert snap.total_positions == 1
        assert snap.active_count    == 1
        b.stop()

    def test_snapshot_stored_in_history(self):
        b = _started_book()
        s = b.snapshot()
        assert b.snapshot_history().count == 1
        b.stop()

    def test_snapshot_emits_event(self):
        b = _started_book()
        b.snapshot()
        evts = [e for e in b.events() if e.event_type == BookEventType.SNAPSHOT_CREATED]
        assert len(evts) == 1
        b.stop()

    def test_snapshot_increments_statistics(self):
        b = _started_book()
        b.snapshot()
        assert b.statistics().total_snapshots == 1
        b.stop()

    def test_filtered_snapshot(self):
        b = _started_book()
        _add_open_position(b, instrument="NIFTY50")
        b.add(_make_position(instrument="BANKNIFTY"))
        snap = b.filtered_snapshot(instrument_filter("NIFTY50"), "nifty-only")
        assert snap.filter_label  == "nifty-only"
        assert snap.total_matched == 1
        b.stop()

    def test_historical_snapshot_retrieval(self):
        b    = _started_book()
        snap = b.snapshot()
        hist = b.historical_snapshot(snap.snapshot_id)
        assert hist is not None
        assert hist.snapshot_id == snap.snapshot_id
        b.stop()

    def test_historical_snapshot_not_found(self):
        b = _started_book()
        assert b.historical_snapshot("ghost") is None
        b.stop()

    def test_latest_snapshot(self):
        b    = _started_book()
        snap = b.snapshot()
        hist = b.latest_snapshot()
        assert hist is not None
        assert hist.snapshot_id == snap.snapshot_id
        b.stop()

    # ── validate ──────────────────────────────────────────────────────────────

    def test_validate_clean_book(self):
        b   = _started_book()
        _add_open_position(b)
        res = b.validate()
        assert res.is_valid is True
        b.stop()

    def test_validate_emits_event(self):
        b = _started_book()
        b.validate()
        evts = [e for e in b.events() if e.event_type == BookEventType.BOOK_VALIDATED]
        assert len(evts) == 1
        b.stop()

    def test_validate_result_to_dict(self):
        b   = _started_book()
        res = b.validate()
        d   = res.to_dict()
        assert "is_valid" in d and "findings" in d
        b.stop()

    # ── statistics ────────────────────────────────────────────────────────────

    def test_statistics_returns_copy(self):
        b  = _started_book()
        s1 = b.statistics()
        s2 = b.statistics()
        assert s1 is not s2
        b.stop()

    def test_statistics_live_counts(self):
        b   = _started_book()
        _add_open_position(b)
        s   = b.statistics()
        assert s.active_positions >= 1
        b.stop()

    # ── history ───────────────────────────────────────────────────────────────

    def test_history_is_book_history(self):
        b = _started_book()
        assert isinstance(b.history(), BookHistory)
        b.stop()

    def test_history_grows_with_operations(self):
        b = _started_book()
        b.add(_make_position())
        assert len(b.history()) >= 1
        b.stop()

    # ── events ────────────────────────────────────────────────────────────────

    def test_events_returns_copy(self):
        b  = _started_book()
        e1 = b.events()
        b.add(_make_position())
        e2 = b.events()
        assert len(e2) > len(e1)
        b.stop()

    # ── is_empty and position_count ───────────────────────────────────────────

    def test_is_empty_on_start(self):
        b = _started_book()
        assert b.is_empty is True
        b.stop()

    def test_is_not_empty_after_add(self):
        b = _started_book()
        b.add(_make_position())
        assert b.is_empty is False
        b.stop()


# ══════════════════════════════════════════════════════════════════════════════
# Concurrency
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_adds(self):
        """50 threads each add a unique position — all must succeed."""
        b      = _started_book(max_positions=200)
        errors: List[Exception] = []

        def add_one():
            try:
                b.add(_make_position())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=add_one) for _ in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == [], f"Errors: {errors}"
        assert b.position_count == 50
        b.stop()

    def test_concurrent_queries(self):
        """10 threads query concurrently — no corruption."""
        b = _started_book()
        for _ in range(10):
            b.add(_make_position())

        errors: List[Exception] = []

        def query_all():
            try:
                b.find(BookQuery())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=query_all) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        b.stop()

    def test_concurrent_snapshots(self):
        """5 threads generate snapshots simultaneously."""
        b = _started_book()
        for _ in range(5):
            b.add(_make_position())

        errors: List[Exception] = []

        def snap():
            try:
                b.snapshot()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=snap) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        b.stop()

    def test_concurrent_index_and_add(self):
        """Interleaved adds and reads must not corrupt index counts."""
        b      = _started_book(max_positions=500)
        errors: List[Exception] = []

        def do_add():
            try:
                b.add(_make_position())
            except Exception as exc:
                errors.append(exc)

        def do_read():
            try:
                b.find_active()
                b.find_by_instrument("NIFTY50")
            except Exception as exc:
                errors.append(exc)

        workers = (
            [threading.Thread(target=do_add)  for _ in range(30)] +
            [threading.Thread(target=do_read) for _ in range(20)]
        )
        for t in workers: t.start()
        for t in workers: t.join()

        assert errors == []
        b.stop()


# ══════════════════════════════════════════════════════════════════════════════
# Regression guards
# ══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_add_does_not_register_on_validation_failure(self):
        b   = _started_book()
        pos = _make_position()
        pos._instrument = ""
        try:
            b.add(pos)
        except PositionBookValidationError:
            pass
        assert b.position_count == 0
        b.stop()

    def test_remove_removes_from_all_indexes(self):
        b   = _started_book()
        pos = _make_position(portfolio_id="port-A", instrument="NIFTY50")
        e   = b.add(pos)
        b.remove(e.position_id)
        assert b.find_by_portfolio("port-A")    == []
        assert b.find_by_instrument("NIFTY50") == []
        b.stop()

    def test_state_change_notification_updates_live_counts(self):
        b   = _started_book()
        pos = _make_position()
        e   = b.add(pos)
        # CREATED — not active
        assert b.statistics().active_positions == 0

        # Transition to OPEN
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        b.notify_state_changed(e.position_id, PositionState.CREATED)
        # After notify for CREATED→OPENING was not called; let's notify for OPENING→OPEN
        b.notify_state_changed(e.position_id, PositionState.OPENING)
        assert b.statistics().active_positions == 1
        b.stop()

    def test_snapshot_is_immutable_copy_not_live(self):
        b    = _started_book()
        snap = b.snapshot()
        b.add(_make_position())
        # Snapshot must reflect old count
        assert snap.total_positions == 0
        assert b.position_count     == 1
        b.stop()

    def test_full_lifecycle_end_to_end(self):
        """add → state-change notifications → remove, with event audit."""
        b = _started_book()

        pos = _make_position(
            instrument="NIFTY50",
            portfolio_id="port-A",
            strategy_id="momentum",
        )
        e = b.add(pos)
        assert b.position_count == 1

        # Advance state: CREATED → OPENING → OPEN
        pos.transition_to(PositionState.OPENING)
        b.notify_state_changed(e.position_id, PositionState.CREATED)
        pos.transition_to(PositionState.OPEN)
        b.notify_state_changed(e.position_id, PositionState.OPENING)

        # Query active
        assert len(b.find_active()) == 1

        # Snapshot
        snap = b.snapshot()
        assert snap.active_count == 1

        # Validate
        result = b.validate()
        assert result.is_valid

        # Close
        pos.transition_to(PositionState.CLOSING)
        b.notify_state_changed(e.position_id, PositionState.OPEN)
        pos.transition_to(PositionState.CLOSED)
        b.notify_state_changed(e.position_id, PositionState.CLOSING)

        assert len(b.find_closed()) == 1

        # Archive
        pos.transition_to(PositionState.ARCHIVED)
        b.notify_state_changed(e.position_id, PositionState.CLOSED)
        assert len(b.find_archived()) == 1

        # Remove from book
        b.remove(e.position_id)
        assert b.position_count == 0
        assert b.is_empty is True

        # Event audit
        types = {ev.event_type for ev in b.events()}
        assert BookEventType.POSITION_ADDED   in types
        assert BookEventType.POSITION_UPDATED in types
        assert BookEventType.SNAPSHOT_CREATED in types
        assert BookEventType.BOOK_VALIDATED   in types
        assert BookEventType.POSITION_REMOVED in types

        stats = b.statistics()
        assert stats.positions_added   == 1
        assert stats.positions_removed == 1
        assert stats.total_snapshots   >= 1
        assert stats.total_queries     == 0  # no explicit queries in this path

        b.stop()

    def test_historical_snapshot_survives_subsequent_mutations(self):
        """Historical snapshot must not be affected by later adds."""
        b = _started_book()
        b.add(_make_position())
        snap = b.snapshot()

        # Add more positions after snapshotting
        b.add(_make_position())
        b.add(_make_position())

        hist = b.historical_snapshot(snap.snapshot_id)
        assert hist is not None
        assert hist.snapshot.total_positions == 1   # frozen at snapshot time

        b.stop()
