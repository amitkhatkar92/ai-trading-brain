"""iios/execution/orders/core/order_execution.py

Represents a single fill event (partial or complete) against an order.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderExecution:
    """Immutable record of a single fill event."""

    fill_id:      str   = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:     str   = ""

    fill_quantity: float = 0.0
    fill_price:    float = 0.0
    fill_value:    float = field(init=False)   # derived

    commission:    float = 0.0
    slippage:      float = 0.0    # signed: negative = favourable
    market_impact: float = 0.0

    venue:         str   = ""     # exchange / broker identifier (broker-agnostic label)
    sequence_no:   int   = 0      # fill sequence within the order

    timestamp:     float = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.fill_value = round(self.fill_quantity * self.fill_price, 8)

    def net_value(self) -> float:
        """fill_value minus commissions."""
        return self.fill_value - self.commission

    def to_dict(self) -> dict[str, Any]:
        return {
            "fill_id":       self.fill_id,
            "order_id":      self.order_id,
            "fill_quantity": self.fill_quantity,
            "fill_price":    self.fill_price,
            "fill_value":    self.fill_value,
            "commission":    self.commission,
            "slippage":      self.slippage,
            "market_impact": self.market_impact,
            "venue":         self.venue,
            "sequence_no":   self.sequence_no,
            "timestamp":     self.timestamp,
            "metadata":      dict(self.metadata),
        }
