"""iios/execution/positions/book/position_book.py
==================================================
PositionBook — the canonical institutional repository for every
position managed by IIOS.

This is NOT a broker position list.
This is NOT a portfolio engine.
This ONLY manages the institutional position book.

Operations
----------
add(position)                       — add a position to the book
update(position_id)                 — re-touch entry, emit POSITION_UPDATED
remove(position_id)                 — remove from book
notify_state_changed(pid, old_state)— refresh LIFECYCLE_STATE index

find(query)                         — structured query → QueryResult
filter(predicate, label)            — custom predicate → QueryResult
find_by_id(position_id)             — O(1) primary lookup
find_by_portfolio(portfolio_id)     — secondary index lookup
find_by_strategy(strategy_id)
find_by_decision(decision_id)
find_by_execution(execution_id)
find_by_workflow(workflow_id)
find_by_instrument(instrument)
find_by_exchange(exchange)
find_active()
find_closed()
find_archived()
find_suspended()

snapshot()                          → PositionBookSnapshot
filtered_snapshot(predicate, label) → FilteredSnapshot
historical_snapshot(snapshot_id)    → Optional[HistoricalSnapshot]

validate()                          → BookValidationResult

statistics()                        → BookStatistics
history()                           → BookHistory
events()                            → List[BookEvent]

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import copy
import threading
import time
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.positions.lifecycle import Position, PositionState

from .constants import (
    ACTOR_BOOK,
    BOOK_SYSTEM_ID,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    DEFAULT_SNAPSHOT_LIMIT,
    VERSION,
    BookOperationType,
)
from .exceptions import (
    BookEntryNotFoundError,
    PositionBookNotRunningError,
    PositionBookQueryError,
)
from .position_book_events import (
    BookEvent,
    make_book_validated_event,
    make_position_added_event,
    make_position_removed_event,
    make_position_updated_event,
    make_snapshot_created_event,
)
from .position_book_factory import BookFactory
from .position_book_history import BookHistory, SnapshotHistory
from .position_book_registry import BookRegistry
from .position_book_snapshot import (
    FilteredSnapshot,
    HistoricalSnapshot,
    PositionBookSnapshot,
    make_book_snapshot,
    make_filtered_snapshot,
)
from .position_book_statistics import BookStatistics
from .position_book_validation import BookValidationResult, BookValidator
from .position_entry import BookEntry
from .position_filter import PositionPredicate
from .position_query import BookQuery, QueryResult, make_query_result

_log   = get_logger(__name__, engine_id=BOOK_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=BOOK_SYSTEM_ID)


class PositionBook(LifecycleAwareMixin):
    """
    Canonical institutional repository for every position managed by IIOS.

    Responsibilities
    ----------------
    * Maintain all active, closed, and archived positions.
    * Provide indexed lookup across 11 dimensions.
    * Generate immutable point-in-time snapshots.
    * Maintain bounded event and snapshot history.
    * Validate internal consistency.
    * Emit domain events on every book mutation.

    Non-responsibilities
    --------------------
    * No portfolio calculations.
    * No risk calculations.
    * No PnL engine.
    * No broker synchronisation.
    * No position reconciliation.
    """

    def __init__(
        self,
        *,
        max_positions:  int = DEFAULT_MAX_POSITIONS,
        max_history:    int = DEFAULT_MAX_HISTORY,
        max_snapshots:  int = DEFAULT_SNAPSHOT_LIMIT,
    ) -> None:
        super().__init__()
        self._registry         = BookRegistry(max_positions=max_positions)
        self._factory          = BookFactory()
        self._validator        = BookValidator()
        self._statistics       = BookStatistics()
        self._history          = BookHistory(max_size=max_history)
        self._snapshot_history = SnapshotHistory(max_size=max_snapshots)
        self._events:           List[BookEvent] = []
        self._lock             = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(BOOK_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("PositionBook started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(BOOK_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info(
            "PositionBook stopped.",
            position_count=self._registry.count,
        )
        self._registry.stop()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(
        self,
        position: Position,
        actor:    str = ACTOR_BOOK,
    ) -> BookEntry:
        """
        Add *position* to the book.

        Creates a ``BookEntry`` via the factory, validates identity
        fields, registers in the book, increments statistics, and
        emits a POSITION_ADDED event.

        Returns
        -------
        BookEntry
            The newly created entry.

        Raises
        ------
        PositionBookNotRunningError
            If the book is not started.
        DuplicateBookEntryError
            If a position with this ID is already in the book.
        PositionBookCapacityError
            If the book is at max capacity.
        PositionBookValidationError
            If the position fails identity validation.
        """
        self._assert_running()
        entry = self._factory.create(position, added_by=actor)
        self._registry.add(entry)

        with self._lock:
            self._statistics.record_added()
            self._refresh_live_counts()

        evt = make_position_added_event(
            position_id=entry.position_id,
            portfolio_id=entry.portfolio_id,
            strategy_id=entry.strategy_id,
            actor=actor,
        )
        self._append_event(evt)

        _log.info(
            "Position added to book.",
            position_id=entry.position_id,
            instrument=entry.instrument,
            state=entry.state.value,
        )
        return entry

    def update(
        self,
        position_id: str,
        actor:       str = ACTOR_BOOK,
    ) -> BookEntry:
        """
        Touch an existing entry and emit a POSITION_UPDATED event.

        Callers should invoke this whenever the underlying position's
        non-state fields change (e.g. price/PnL updates) so the book's
        event history reflects the mutation.  For state transitions,
        use ``notify_state_changed()`` instead.

        Raises
        ------
        BookEntryNotFoundError
            If the position is not in the book.
        """
        self._assert_running()
        entry = self._registry.require(position_id)
        entry.touch()

        evt = make_position_updated_event(
            position_id=entry.position_id,
            portfolio_id=entry.portfolio_id,
            strategy_id=entry.strategy_id,
            actor=actor,
        )
        self._append_event(evt)
        _log.debug("Position updated in book.", position_id=position_id)
        return entry

    def remove(
        self,
        position_id: str,
        actor:       str = ACTOR_BOOK,
    ) -> BookEntry:
        """
        Remove a position from the book.

        Raises
        ------
        PositionBookNotRunningError
            If the book is not started.
        BookEntryNotFoundError
            If the position is not in the book.
        """
        self._assert_running()
        entry = self._registry.require(position_id)
        portfolio_id = entry.portfolio_id
        strategy_id  = entry.strategy_id
        self._registry.remove(position_id)

        with self._lock:
            self._statistics.record_removed()
            self._refresh_live_counts()

        evt = make_position_removed_event(
            position_id=position_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            actor=actor,
        )
        self._append_event(evt)
        _log.info("Position removed from book.", position_id=position_id)
        return entry

    def notify_state_changed(
        self,
        position_id: str,
        old_state:   PositionState,
        actor:       str = ACTOR_BOOK,
    ) -> None:
        """
        Notify the book that a position has transitioned state.

        Updates the LIFECYCLE_STATE index, refreshes live state counts,
        and emits a POSITION_UPDATED event.

        Must be called *after* the position's state has already changed.

        Raises
        ------
        BookEntryNotFoundError
            If the position is not in the book.
        """
        self._assert_running()
        entry = self._registry.require(position_id)
        self._registry.notify_state_changed(entry, old_state)

        with self._lock:
            self._refresh_live_counts()

        evt = make_position_updated_event(
            position_id=position_id,
            portfolio_id=entry.portfolio_id,
            strategy_id=entry.strategy_id,
            actor=actor,
            metadata={"old_state": old_state.value, "new_state": entry.state.value},
        )
        self._append_event(evt)
        _log.debug(
            "State change notified.",
            position_id=position_id,
            old_state=old_state.value,
            new_state=entry.state.value,
        )

    # ── Query ─────────────────────────────────────────────────────────────────

    def find(self, query: BookQuery) -> QueryResult:
        """
        Execute a structured ``BookQuery`` and return a ``QueryResult``.

        Uses the most appropriate index path:
        1. Single-lookup: O(1) primary index when only position_id is set.
        2. Index query: O(k) secondary index for single-filter queries.
        3. Full scan + filter for multi-field or custom-filter queries.

        Raises
        ------
        PositionBookQueryError
            If the query limit is invalid.
        """
        self._assert_running()
        if query.limit <= 0:
            raise PositionBookQueryError("Query limit must be > 0")

        t0 = time.perf_counter()
        entries = self._execute_query(query)
        elapsed_ms = (time.perf_counter() - t0) * 1_000

        with self._lock:
            self._statistics.record_query(elapsed_ms)

        _log.debug(
            "Query executed.",
            count=len(entries),
            elapsed_ms=round(elapsed_ms, 3),
        )
        return make_query_result(entries, elapsed_ms)

    def filter(
        self,
        predicate:   PositionPredicate,
        label:       str = "custom",
    ) -> QueryResult:
        """
        Apply a custom ``PositionPredicate`` and return a ``QueryResult``.

        Performs a full scan.
        """
        self._assert_running()
        t0 = time.perf_counter()
        entries = [e for e in self._registry.all() if predicate(e.position)]
        elapsed_ms = (time.perf_counter() - t0) * 1_000

        with self._lock:
            self._statistics.record_query(elapsed_ms)

        return make_query_result(entries, elapsed_ms)

    # ── Convenience lookups ───────────────────────────────────────────────────

    def find_by_id(self, position_id: str) -> Optional[BookEntry]:
        """O(1) primary index lookup.  Returns ``None`` if not found."""
        self._assert_running()
        entry = self._registry.get(position_id)
        if entry:
            entry.touch()
        return entry

    def require_by_id(self, position_id: str) -> BookEntry:
        """O(1) lookup; raises ``BookEntryNotFoundError`` if not found."""
        entry = self.find_by_id(position_id)
        if entry is None:
            raise BookEntryNotFoundError(position_id)
        return entry

    def find_by_portfolio(self, portfolio_id: str) -> List[BookEntry]:
        self._assert_running()
        return self._registry.by_portfolio(portfolio_id)

    def find_by_strategy(self, strategy_id: str) -> List[BookEntry]:
        self._assert_running()
        return self._registry.by_strategy(strategy_id)

    def find_by_decision(self, decision_id: str) -> List[BookEntry]:
        self._assert_running()
        return self._registry.by_decision(decision_id)

    def find_by_execution(self, execution_id: str) -> List[BookEntry]:
        self._assert_running()
        return self._registry.by_execution(execution_id)

    def find_by_workflow(self, workflow_id: str) -> List[BookEntry]:
        self._assert_running()
        return self._registry.by_workflow(workflow_id)

    def find_by_instrument(self, instrument: str) -> List[BookEntry]:
        self._assert_running()
        return self._registry.by_instrument(instrument)

    def find_by_exchange(self, exchange: str) -> List[BookEntry]:
        self._assert_running()
        return self._registry.by_exchange(exchange)

    def find_active(self) -> List[BookEntry]:
        self._assert_running()
        return self._registry.active()

    def find_closed(self) -> List[BookEntry]:
        self._assert_running()
        return self._registry.closed()

    def find_archived(self) -> List[BookEntry]:
        self._assert_running()
        return self._registry.archived()

    def find_suspended(self) -> List[BookEntry]:
        self._assert_running()
        return self._registry.suspended()

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def snapshot(self) -> PositionBookSnapshot:
        """
        Generate a full, immutable ``PositionBookSnapshot``.

        The snapshot is stored in snapshot history and a SNAPSHOT_CREATED
        event is emitted.
        """
        self._assert_running()
        with self._lock:
            stats_copy  = copy.copy(self._statistics)
            self._refresh_live_counts()
        entries = self._registry.all()
        snap    = make_book_snapshot(entries, stats_copy)

        self._snapshot_history.append(snap)
        with self._lock:
            self._statistics.record_snapshot()

        evt = make_snapshot_created_event(
            metadata={"snapshot_id": snap.snapshot_id, "total": snap.total_positions},
        )
        self._append_event(evt)

        _log.info(
            "Book snapshot generated.",
            snapshot_id=snap.snapshot_id,
            total_positions=snap.total_positions,
        )
        return snap

    def filtered_snapshot(
        self,
        predicate:    PositionPredicate,
        filter_label: str = "custom",
    ) -> FilteredSnapshot:
        """
        Generate a ``FilteredSnapshot`` of the subset matching *predicate*.
        """
        self._assert_running()
        entries = [e for e in self._registry.all() if predicate(e.position)]
        snap    = make_filtered_snapshot(entries, filter_label)

        with self._lock:
            self._statistics.record_snapshot()

        _log.debug(
            "Filtered snapshot generated.",
            filter_label=filter_label,
            matched=snap.total_matched,
        )
        return snap

    def historical_snapshot(
        self,
        snapshot_id: str,
    ) -> Optional[HistoricalSnapshot]:
        """
        Retrieve a past snapshot from history by its snapshot_id.

        Returns ``None`` if not found (may have been evicted).
        """
        return self._snapshot_history.get_by_id(snapshot_id)

    def latest_snapshot(self) -> Optional[HistoricalSnapshot]:
        """Return the most recently generated snapshot, or ``None``."""
        return self._snapshot_history.latest()

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self) -> BookValidationResult:
        """
        Run all consistency checks against the current book state.

        Emits a BOOK_VALIDATED event regardless of the result.

        Returns
        -------
        BookValidationResult
            is_valid is True when no ERROR-severity findings are produced.
        """
        self._assert_running()
        result = self._validator.validate_all(self._registry)

        evt = make_book_validated_event(
            metadata={
                "is_valid":     result.is_valid,
                "error_count":  result.error_count,
                "warning_count": result.warning_count,
            },
        )
        self._append_event(evt)

        _log.info(
            "Book validated.",
            is_valid=result.is_valid,
            errors=result.error_count,
            warnings=result.warning_count,
        )
        return result

    # ── Observability ─────────────────────────────────────────────────────────

    def statistics(self) -> BookStatistics:
        """Return a copy of the current book statistics."""
        with self._lock:
            self._refresh_live_counts()
            return copy.copy(self._statistics)

    def history(self) -> BookHistory:
        """Return the event history (reference, not a copy)."""
        return self._history

    def snapshot_history(self) -> SnapshotHistory:
        """Return the snapshot history (reference, not a copy)."""
        return self._snapshot_history

    def events(self) -> List[BookEvent]:
        """Return a copy of the accumulated event list."""
        with self._lock:
            return list(self._events)

    # ── Direct registry access ────────────────────────────────────────────────

    @property
    def registry(self) -> BookRegistry:
        return self._registry

    @property
    def position_count(self) -> int:
        return self._registry.count

    @property
    def is_empty(self) -> bool:
        return self._registry.is_empty

    # ── Private helpers ───────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionBookNotRunningError()

    def _append_event(self, event: BookEvent) -> None:
        with self._lock:
            self._events.append(event)
        self._history.append(event)

    def _refresh_live_counts(self) -> None:
        """Recompute live state counts from the index (caller holds self._lock)."""
        idx = self._registry.index
        self._statistics.update_live_counts(
            active=len(idx.active()),
            closed=len(idx.closed()),
            archived=len(idx.archived()),
            suspended=len(idx.suspended()),
        )
        self._statistics.update_index_utilization(idx.utilization())

    def _execute_query(self, query: BookQuery) -> List[BookEntry]:
        """Select the optimal query path and return matching entries."""
        # 1. Single primary-key lookup
        if query.is_single_lookup:
            entry = self._registry.get(query.position_id)  # type: ignore[arg-type]
            return [entry] if entry else []

        # 2. Select best secondary index (first set filter wins)
        candidates: Optional[List[BookEntry]] = None

        if query.portfolio_id is not None:
            candidates = self._registry.by_portfolio(query.portfolio_id)
        elif query.strategy_id is not None:
            candidates = self._registry.by_strategy(query.strategy_id)
        elif query.decision_id is not None:
            candidates = self._registry.by_decision(query.decision_id)
        elif query.execution_id is not None:
            candidates = self._registry.by_execution(query.execution_id)
        elif query.workflow_id is not None:
            candidates = self._registry.by_workflow(query.workflow_id)
        elif query.instrument is not None:
            candidates = self._registry.by_instrument(query.instrument)
        elif query.exchange is not None:
            candidates = self._registry.by_exchange(query.exchange)
        elif query.product is not None:
            candidates = self._registry.by_product(query.product.value)
        elif query.direction is not None:
            candidates = self._registry.by_direction(query.direction.value)
        elif query.state is not None:
            candidates = self._registry.by_state(query.state)
        else:
            candidates = self._registry.all()

        # 3. Apply remaining field filters to the candidate set
        results = self._apply_field_filters(candidates, query)

        # 4. Apply custom predicate
        if query.custom_filter is not None:
            results = [e for e in results if query.custom_filter(e.position)]

        return results[: query.limit]

    def _apply_field_filters(
        self,
        entries: List[BookEntry],
        query:   BookQuery,
    ) -> List[BookEntry]:
        """Apply remaining field filters (those not used for index selection)."""
        out = entries
        if query.position_id is not None:
            out = [e for e in out if e.position_id == query.position_id]
        if query.portfolio_id is not None:
            out = [e for e in out if e.portfolio_id == query.portfolio_id]
        if query.strategy_id is not None:
            out = [e for e in out if e.strategy_id == query.strategy_id]
        if query.decision_id is not None:
            out = [e for e in out if e.decision_id == query.decision_id]
        if query.execution_id is not None:
            out = [e for e in out if e.execution_id == query.execution_id]
        if query.workflow_id is not None:
            out = [e for e in out if e.workflow_id == query.workflow_id]
        if query.instrument is not None:
            out = [e for e in out if e.instrument == query.instrument]
        if query.exchange is not None:
            out = [e for e in out if e.exchange == query.exchange]
        if query.product is not None:
            out = [e for e in out if e.product == query.product]
        if query.direction is not None:
            out = [e for e in out if e.direction == query.direction]
        if query.state is not None:
            out = [e for e in out if e.state == query.state]
        return out
