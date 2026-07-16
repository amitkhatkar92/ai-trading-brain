"""iios/execution/positions/book/position_book_registry.py
==================================================
BookRegistry — LifecycleAwareMixin storage layer for the Position Book.

Owns a ``PositionIndex`` for O(1) multi-key lookups and a capacity guard.
All write operations require the registry to be in the RUNNING state.
Read operations are always permitted.

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import threading
from typing import List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_MAX_POSITIONS,
    REGISTRY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    BookEntryNotFoundError,
    DuplicateBookEntryError,
    PositionBookCapacityError,
    PositionBookNotRunningError,
)
from .position_entry import BookEntry
from .position_index import PositionIndex
from iios.execution.positions.lifecycle import PositionState

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class BookRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry and multi-key index for the Position Book.

    Owns a ``PositionIndex`` that maintains 11 concurrent indexes over
    ``BookEntry`` objects.  Capacity is enforced atomically.

    Read operations (get, all, filters) are permitted regardless of
    lifecycle state to allow inspection after shutdown.
    Write operations (add, remove, notify_state_changed) require
    the registry to be in the RUNNING state.
    """

    def __init__(self, max_positions: int = DEFAULT_MAX_POSITIONS) -> None:
        super().__init__()
        self._max   = max(1, max_positions)
        self._index = PositionIndex()
        self._lock  = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("BookRegistry started.", max_positions=self._max)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("BookRegistry stopped.", position_count=self._index.count())

    # ── Write ─────────────────────────────────────────────────────────────────

    def add(self, entry: BookEntry) -> None:
        """
        Add *entry* to the registry and all 11 indexes.

        Raises
        ------
        PositionBookNotRunningError
            If the registry is not started.
        PositionBookCapacityError
            If the registry is at maximum capacity.
        DuplicateBookEntryError
            If a position with the same position_id already exists.
        """
        self._assert_running()
        pid = entry.position_id
        with self._lock:
            if self._index.count() >= self._max:
                raise PositionBookCapacityError(self._max)
            if self._index.contains(pid):
                raise DuplicateBookEntryError(pid)
            self._index.add(entry)

        _log.info(
            "Entry added to book.",
            position_id=pid,
            instrument=entry.instrument,
            state=entry.state.value,
        )

    def remove(self, position_id: str) -> BookEntry:
        """
        Remove and return the entry for *position_id*.

        Raises
        ------
        PositionBookNotRunningError
            If the registry is not started.
        BookEntryNotFoundError
            If the position is not in the book.
        """
        self._assert_running()
        with self._lock:
            entry = self._index.get(position_id)
            if entry is None:
                raise BookEntryNotFoundError(position_id)
            self._index.remove(entry)

        _log.info("Entry removed from book.", position_id=position_id)
        return entry

    def notify_state_changed(
        self,
        entry:     BookEntry,
        old_state: PositionState,
    ) -> None:
        """
        Update the LIFECYCLE_STATE index after a position has transitioned state.

        Must be called *after* the position's state has already changed so
        ``entry.state`` reflects the new value.
        """
        self._assert_running()
        self._index.reindex_state(entry, old_state)
        _log.debug(
            "State index updated.",
            position_id=entry.position_id,
            old_state=old_state.value,
            new_state=entry.state.value,
        )

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, position_id: str) -> Optional[BookEntry]:
        """O(1) primary lookup.  Returns ``None`` if not found."""
        return self._index.get(position_id)

    def require(self, position_id: str) -> BookEntry:
        """
        Return the entry for *position_id* or raise ``BookEntryNotFoundError``.
        """
        entry = self._index.get(position_id)
        if entry is None:
            raise BookEntryNotFoundError(position_id)
        return entry

    def contains(self, position_id: str) -> bool:
        return self._index.contains(position_id)

    def all(self) -> List[BookEntry]:
        return self._index.all()

    @property
    def count(self) -> int:
        return self._index.count()

    @property
    def is_empty(self) -> bool:
        return self._index.count() == 0

    @property
    def index(self) -> PositionIndex:
        return self._index

    # ── Filtered reads (delegate to index) ───────────────────────────────────

    def by_portfolio(self, portfolio_id: str) -> List[BookEntry]:
        return self._index.by_portfolio(portfolio_id)

    def by_strategy(self, strategy_id: str) -> List[BookEntry]:
        return self._index.by_strategy(strategy_id)

    def by_decision(self, decision_id: str) -> List[BookEntry]:
        return self._index.by_decision(decision_id)

    def by_execution(self, execution_id: str) -> List[BookEntry]:
        return self._index.by_execution(execution_id)

    def by_workflow(self, workflow_id: str) -> List[BookEntry]:
        return self._index.by_workflow(workflow_id)

    def by_instrument(self, instrument: str) -> List[BookEntry]:
        return self._index.by_instrument(instrument)

    def by_exchange(self, exchange: str) -> List[BookEntry]:
        return self._index.by_exchange(exchange)

    def by_product(self, product_value: str) -> List[BookEntry]:
        return self._index.by_product(product_value)

    def by_direction(self, direction_value: str) -> List[BookEntry]:
        return self._index.by_direction(direction_value)

    def by_state(self, state: PositionState) -> List[BookEntry]:
        return self._index.by_state(state)

    def active(self) -> List[BookEntry]:
        return self._index.active()

    def closed(self) -> List[BookEntry]:
        return self._index.closed()

    def archived(self) -> List[BookEntry]:
        return self._index.archived()

    def suspended(self) -> List[BookEntry]:
        return self._index.suspended()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionBookNotRunningError()
