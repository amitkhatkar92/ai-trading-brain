"""iios/execution/oms/order_book/order_book_entry.py
==================================================
OrderBookEntry — the canonical record stored in the Order Book
for each known order.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from iios.execution.oms.order_book.constants import (
    BookEntryStatus,
    ORDER_STATE_TO_BOOK_STATUS,
    TERMINAL_BOOK_STATUSES,
    VERSION,
)


@dataclass
class OrderBookEntry:
    """
    Mutable record for a single order in the IIOS Order Book.

    The Order Book owns one entry per order_id.
    Entries are updated in-place as the underlying M1 order
    state advances.  Snapshots are produced on demand.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    entry_id:      str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:      str = ""

    # ── Cross-references ──────────────────────────────────────────────────────
    portfolio_id:  str = ""
    strategy_id:   str = ""
    decision_id:   str = ""
    execution_id:  str = ""
    workflow_id:   str = ""
    broker_id:     str = ""

    # ── Instrument ────────────────────────────────────────────────────────────
    instrument:    str = ""
    exchange:      str = ""
    order_type:    str = ""   # MARKET / LIMIT / STOP / …
    side:          str = ""   # BUY / SELL

    # ── Status ────────────────────────────────────────────────────────────────
    status:        BookEntryStatus = BookEntryStatus.ACTIVE
    order_state:   str             = ""   # raw M1 OrderState value

    # ── Quantity / price ──────────────────────────────────────────────────────
    quantity:       Decimal = Decimal("0")
    filled_quantity: Decimal = Decimal("0")
    limit_price:    Optional[Decimal] = None
    average_price:  Optional[Decimal] = None

    # ── Timing ────────────────────────────────────────────────────────────────
    added_at:      float = field(default_factory=time.time)
    updated_at:    float = field(default_factory=time.time)

    # ── Metadata ──────────────────────────────────────────────────────────────
    tags:          frozenset[str]  = field(default_factory=frozenset)
    metadata:      dict[str, Any]  = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.status == BookEntryStatus.ACTIVE

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_BOOK_STATUSES

    @property
    def fill_ratio(self) -> float:
        if self.quantity == 0:
            return 0.0
        return float(self.filled_quantity / self.quantity)

    @property
    def unfilled_quantity(self) -> Decimal:
        return max(Decimal("0"), self.quantity - self.filled_quantity)

    @property
    def age_sec(self) -> float:
        return time.time() - self.added_at

    # ── Mutation ──────────────────────────────────────────────────────────────

    def apply_state_update(
        self,
        new_order_state: str,
        *,
        filled_quantity:  Decimal | None = None,
        average_price:    Decimal | None = None,
    ) -> None:
        """Update entry with new M1 OrderState."""
        self.order_state = new_order_state
        self.status      = ORDER_STATE_TO_BOOK_STATUS.get(
            new_order_state, BookEntryStatus.UNKNOWN
        )
        if filled_quantity is not None:
            self.filled_quantity = filled_quantity
        if average_price is not None:
            self.average_price = average_price
        self.updated_at = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":        self.entry_id,
            "order_id":        self.order_id,
            "portfolio_id":    self.portfolio_id,
            "strategy_id":     self.strategy_id,
            "decision_id":     self.decision_id,
            "execution_id":    self.execution_id,
            "workflow_id":     self.workflow_id,
            "broker_id":       self.broker_id,
            "instrument":      self.instrument,
            "exchange":        self.exchange,
            "order_type":      self.order_type,
            "side":            self.side,
            "status":          self.status.value,
            "order_state":     self.order_state,
            "quantity":        str(self.quantity),
            "filled_quantity": str(self.filled_quantity),
            "limit_price":     str(self.limit_price) if self.limit_price else None,
            "average_price":   str(self.average_price) if self.average_price else None,
            "fill_ratio":      round(self.fill_ratio, 4),
            "is_active":       self.is_active,
            "is_terminal":     self.is_terminal,
            "added_at":        self.added_at,
            "updated_at":      self.updated_at,
            "tags":            sorted(self.tags),
        }

    def __repr__(self) -> str:
        return (
            f"OrderBookEntry("
            f"order={self.order_id!r}, "
            f"status={self.status.value}, "
            f"instrument={self.instrument!r})"
        )
