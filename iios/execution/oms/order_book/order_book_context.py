"""iios/execution/oms/order_book/order_book_context.py
==================================================
OrderBookContext — immutable context for an order book operation.
OrderAddRequest  — parameters for adding an entry to the book.
OrderUpdateRequest — parameters for updating an existing entry.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional


@dataclass(frozen=True)
class OrderBookContext:
    """
    Immutable context snapshot for a single order book operation.
    Carries the operation's identity, actor, and timing.
    """
    context_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    operation:      str   = ""
    order_id:       str   = ""
    actor:          str   = "iios:system"
    correlation_id: str   = ""
    occurred_at:    float = field(default_factory=time.time)
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "operation":      self.operation,
            "order_id":       self.order_id,
            "actor":          self.actor,
            "correlation_id": self.correlation_id,
            "occurred_at":    self.occurred_at,
        }


@dataclass
class OrderAddRequest:
    """Parameters for adding a new entry to the Order Book."""

    order_id:      str = ""
    portfolio_id:  str = ""
    strategy_id:   str = ""
    decision_id:   str = ""
    execution_id:  str = ""
    workflow_id:   str = ""
    broker_id:     str = ""
    instrument:    str = ""
    exchange:      str = ""
    order_type:    str = ""
    side:          str = ""
    order_state:   str = ""
    quantity:      Decimal = Decimal("0")
    limit_price:   Optional[Decimal] = None
    tags:          frozenset[str] = field(default_factory=frozenset)
    metadata:      dict[str, Any] = field(default_factory=dict)
    actor:         str = "iios:system"
    correlation_id: str = ""


@dataclass
class OrderUpdateRequest:
    """Parameters for updating an existing Order Book entry."""

    order_id:        str = ""
    new_order_state: str = ""
    filled_quantity: Optional[Decimal] = None
    average_price:   Optional[Decimal] = None
    actor:           str = "iios:system"
    correlation_id:  str = ""
    reason:          str = ""
