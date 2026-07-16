"""iios/execution/positions/book/position_book_snapshot.py
==================================================
Immutable snapshot types for the IIOS Position Book.

BookEntrySnapshot    — full per-entry snapshot (all position fields)
PositionBookSnapshot — full point-in-time snapshot of the entire book
FilteredSnapshot     — snapshot of a predicate-filtered subset
HistoricalSnapshot   — wrapper referencing a past PositionBookSnapshot

Factory functions
-----------------
make_book_snapshot(entries, statistics)     → PositionBookSnapshot
make_filtered_snapshot(entries, label)      → FilteredSnapshot
make_historical_snapshot(snapshot)          → HistoricalSnapshot

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from iios.execution.positions.lifecycle import (
    ACTIVE_STATES,
    SUSPENDED_STATES,
    TERMINAL_STATES,
)

from .constants import VERSION
from .position_book_statistics import BookStatistics

if TYPE_CHECKING:
    from .position_entry import BookEntry


# ── BookEntrySnapshot ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BookEntrySnapshot:
    """
    Full, immutable snapshot of a single book entry.

    All Decimal fields are stored as strings to ensure serialisation
    fidelity and avoid floating-point issues.
    """

    position_id:         str
    entry_id:            str
    instrument:          str
    exchange:            str
    product:             str
    direction:           str
    state:               str
    quantity:            str
    open_quantity:       str
    closed_quantity:     str
    average_entry_price: str
    average_exit_price:  str
    realized_pnl:        str
    unrealized_pnl:      str
    portfolio_id:        str
    strategy_id:         str
    decision_id:         str
    workflow_id:         str
    execution_id:        str
    created_at:          float
    updated_at:          float
    added_at:            float
    added_by:            str

    @classmethod
    def from_entry(cls, entry: "BookEntry") -> "BookEntrySnapshot":
        pos = entry.position
        return cls(
            position_id=pos.position_id,
            entry_id=entry.entry_id,
            instrument=pos.instrument,
            exchange=pos.exchange,
            product=pos.product.value,
            direction=pos.direction.value,
            state=pos.state.value,
            quantity=str(pos.quantity),
            open_quantity=str(pos.open_quantity),
            closed_quantity=str(pos.closed_quantity),
            average_entry_price=str(pos.average_entry_price),
            average_exit_price=str(pos.average_exit_price),
            realized_pnl=str(pos.realized_pnl),
            unrealized_pnl=str(pos.unrealized_pnl),
            portfolio_id=pos.portfolio_id,
            strategy_id=pos.strategy_id,
            decision_id=pos.decision_id,
            workflow_id=pos.workflow_id,
            execution_id=pos.execution_id,
            created_at=pos.created_at,
            updated_at=pos.updated_at,
            added_at=entry.added_at,
            added_by=entry.added_by,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id":          self.position_id,
            "entry_id":             self.entry_id,
            "instrument":           self.instrument,
            "exchange":             self.exchange,
            "product":              self.product,
            "direction":            self.direction,
            "state":                self.state,
            "quantity":             self.quantity,
            "open_quantity":        self.open_quantity,
            "closed_quantity":      self.closed_quantity,
            "average_entry_price":  self.average_entry_price,
            "average_exit_price":   self.average_exit_price,
            "realized_pnl":         self.realized_pnl,
            "unrealized_pnl":       self.unrealized_pnl,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "decision_id":          self.decision_id,
            "workflow_id":          self.workflow_id,
            "execution_id":         self.execution_id,
            "created_at":           self.created_at,
            "updated_at":           self.updated_at,
            "added_at":             self.added_at,
            "added_by":             self.added_by,
        }


# ── PositionBookSnapshot ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class PositionBookSnapshot:
    """
    Full, immutable, point-in-time snapshot of the Position Book.

    Captures all live entries, aggregate counts, and book statistics.
    Produced by ``PositionBook.snapshot()``.
    """

    snapshot_id:     str
    total_positions: int
    active_count:    int
    closed_count:    int
    archived_count:  int
    suspended_count: int
    entries:         Tuple[BookEntrySnapshot, ...]
    statistics:      BookStatistics
    taken_at:        float
    version:         str = VERSION
    metadata:        Dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def is_empty(self) -> bool:
        return self.total_positions == 0

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":     self.snapshot_id,
            "total_positions": self.total_positions,
            "active_count":    self.active_count,
            "closed_count":    self.closed_count,
            "archived_count":  self.archived_count,
            "suspended_count": self.suspended_count,
            "entry_count":     self.entry_count,
            "statistics":      self.statistics.to_dict(),
            "taken_at":        self.taken_at,
            "version":         self.version,
        }


# ── FilteredSnapshot ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FilteredSnapshot:
    """
    Immutable snapshot of a predicate-filtered subset of the Position Book.

    Produced by ``PositionBook.filtered_snapshot(predicate, label)``.
    """

    snapshot_id:   str
    filter_label:  str
    total_matched: int
    entries:       Tuple[BookEntrySnapshot, ...]
    taken_at:      float
    version:       str = VERSION
    metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def is_empty(self) -> bool:
        return self.total_matched == 0

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":   self.snapshot_id,
            "filter_label":  self.filter_label,
            "total_matched": self.total_matched,
            "entry_count":   self.entry_count,
            "taken_at":      self.taken_at,
            "version":       self.version,
        }


# ── HistoricalSnapshot ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HistoricalSnapshot:
    """
    A timestamped reference to a past ``PositionBookSnapshot``
    retrieved from the book's snapshot history.
    """

    reference_id: str
    snapshot:     PositionBookSnapshot
    retrieved_at: float

    @property
    def taken_at(self) -> float:
        return self.snapshot.taken_at

    @property
    def age_seconds(self) -> float:
        return time.time() - self.taken_at

    @property
    def snapshot_id(self) -> str:
        return self.snapshot.snapshot_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "snapshot_id":  self.snapshot.snapshot_id,
            "taken_at":     self.taken_at,
            "retrieved_at": self.retrieved_at,
            "age_seconds":  self.age_seconds,
        }


# ── Factories ─────────────────────────────────────────────────────────────────

def make_book_snapshot(
    entries_list: List["BookEntry"],
    statistics:   BookStatistics,
) -> PositionBookSnapshot:
    """Build a ``PositionBookSnapshot`` from the live entry list."""
    active_count    = sum(1 for e in entries_list if e.state in ACTIVE_STATES)
    archived_count  = sum(1 for e in entries_list if e.state in TERMINAL_STATES)
    suspended_count = sum(1 for e in entries_list if e.state in SUSPENDED_STATES)
    closed_count    = (
        len(entries_list) - active_count - archived_count - suspended_count
    )
    return PositionBookSnapshot(
        snapshot_id=str(uuid.uuid4()),
        total_positions=len(entries_list),
        active_count=active_count,
        closed_count=max(0, closed_count),
        archived_count=archived_count,
        suspended_count=suspended_count,
        entries=tuple(BookEntrySnapshot.from_entry(e) for e in entries_list),
        statistics=statistics,
        taken_at=time.time(),
    )


def make_filtered_snapshot(
    entries_list: List["BookEntry"],
    filter_label: str,
) -> FilteredSnapshot:
    """Build a ``FilteredSnapshot`` from a filtered entry list."""
    return FilteredSnapshot(
        snapshot_id=str(uuid.uuid4()),
        filter_label=filter_label,
        total_matched=len(entries_list),
        entries=tuple(BookEntrySnapshot.from_entry(e) for e in entries_list),
        taken_at=time.time(),
    )


def make_historical_snapshot(snapshot: PositionBookSnapshot) -> HistoricalSnapshot:
    """Wrap a past snapshot in a ``HistoricalSnapshot`` reference."""
    return HistoricalSnapshot(
        reference_id=str(uuid.uuid4()),
        snapshot=snapshot,
        retrieved_at=time.time(),
    )
