"""iios/execution/positions/book/position_entry.py
==================================================
BookEntry — an institutional position entry in the Position Book.

Wraps a live Position with book-level metadata: entry ID, who added
it, when it was added, and last-seen timestamp.

Delegate properties provide direct access to all Position fields
needed by the index and filter layers without exposing the internal
Position reference.

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict

from iios.execution.positions.lifecycle import (
    Position,
    PositionDirection,
    PositionProduct,
    PositionState,
)

from .constants import ACTOR_BOOK, VERSION


class BookEntry:
    """
    A single position entry in the institutional Position Book.

    Responsibilities
    ----------------
    * Wrap a live ``Position`` with immutable book metadata.
    * Expose delegate properties for all 11 indexed dimensions.
    * Track ``last_seen_at`` for freshness checks.
    * Produce a ``to_dict()`` snapshot for serialisation.

    Non-responsibilities
    --------------------
    * No state machine logic — the Position handles its own state.
    * No index management — PositionIndex owns that.
    * No validation — BookValidator owns that.
    """

    __slots__ = (
        "_entry_id",
        "_position",
        "_added_at",
        "_added_by",
        "_last_seen_at",
        "_lock",
    )

    def __init__(
        self,
        position: Position,
        added_by: str = ACTOR_BOOK,
    ) -> None:
        now = time.time()
        self._entry_id     = str(uuid.uuid4())
        self._position     = position
        self._added_at     = now
        self._added_by     = added_by
        self._last_seen_at = now
        self._lock         = threading.Lock()

    # ── Book metadata ─────────────────────────────────────────────────────────

    @property
    def entry_id(self) -> str:
        return self._entry_id

    @property
    def position(self) -> Position:
        return self._position

    @property
    def added_at(self) -> float:
        return self._added_at

    @property
    def added_by(self) -> str:
        return self._added_by

    @property
    def last_seen_at(self) -> float:
        with self._lock:
            return self._last_seen_at

    def touch(self) -> None:
        """Refresh the last-seen timestamp."""
        with self._lock:
            self._last_seen_at = time.time()

    # ── Position identity delegates ───────────────────────────────────────────

    @property
    def position_id(self) -> str:
        return self._position.position_id

    @property
    def portfolio_id(self) -> str:
        return self._position.portfolio_id

    @property
    def strategy_id(self) -> str:
        return self._position.strategy_id

    @property
    def decision_id(self) -> str:
        return self._position.decision_id

    @property
    def workflow_id(self) -> str:
        return self._position.workflow_id

    @property
    def execution_id(self) -> str:
        return self._position.execution_id

    # ── Instrument delegates ──────────────────────────────────────────────────

    @property
    def instrument(self) -> str:
        return self._position.instrument

    @property
    def exchange(self) -> str:
        return self._position.exchange

    @property
    def product(self) -> PositionProduct:
        return self._position.product

    @property
    def direction(self) -> PositionDirection:
        return self._position.direction

    # ── Lifecycle delegate ────────────────────────────────────────────────────

    @property
    def state(self) -> PositionState:
        return self._position.state

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":     self._entry_id,
            "position_id":  self.position_id,
            "instrument":   self.instrument,
            "exchange":     self.exchange,
            "product":      self.product.value,
            "direction":    self.direction.value,
            "state":        self.state.value,
            "portfolio_id": self.portfolio_id,
            "strategy_id":  self.strategy_id,
            "decision_id":  self.decision_id,
            "workflow_id":  self.workflow_id,
            "execution_id": self.execution_id,
            "added_at":     self._added_at,
            "added_by":     self._added_by,
            "last_seen_at": self.last_seen_at,
            "version":      VERSION,
        }

    def __repr__(self) -> str:
        return (
            f"BookEntry(entry_id={self._entry_id!r}, "
            f"position_id={self.position_id!r}, "
            f"state={self.state.value!r})"
        )
