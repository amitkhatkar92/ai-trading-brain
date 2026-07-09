"""iios/execution/orders/core/order_response.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..order_constants import OrderStatus

if TYPE_CHECKING:
    from .order import Order


@dataclass
class OrderResponse:
    """Returned by the OMS after every order submission or operation."""

    response_id:       str         = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:          str         = ""
    request_id:        str         = ""
    status:            OrderStatus = OrderStatus.DRAFT
    success:           bool        = True
    validation_passed: bool        = True
    errors:            list[str]   = field(default_factory=list)
    warnings:          list[str]   = field(default_factory=list)
    order:             Any         = None    # Order | None  (Any to avoid import complexity)
    duration_ms:       float       = 0.0
    timestamp:         float       = field(default_factory=time.time)
    metadata:          dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id":       self.response_id,
            "order_id":          self.order_id,
            "request_id":        self.request_id,
            "status":            self.status.value,
            "success":           self.success,
            "validation_passed": self.validation_passed,
            "errors":            list(self.errors),
            "warnings":          list(self.warnings),
            "order":             self.order.to_dict() if self.order is not None else None,
            "duration_ms":       self.duration_ms,
            "timestamp":         self.timestamp,
            "metadata":          dict(self.metadata),
        }
