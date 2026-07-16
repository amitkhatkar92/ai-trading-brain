"""iios/execution/oms/order_manager/order_manager_response.py
==================================================
Response dataclasses for Order Manager operations.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.oms.order_manager.order_manager_context import ManagedOrder


@dataclass(frozen=True)
class OrderManagerResponse:
    """Base response for all Order Manager operations."""

    response_id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:     str = ""
    operation:      str = ""
    order_id:       str = ""
    succeeded:      bool = True
    error_message:  str  = ""
    error_code:     str  = ""
    responded_at:   float = field(default_factory=time.time)
    duration_ms:    float = 0.0
    managed_order:  Optional[ManagedOrder] = None
    metadata:       dict[str, Any] = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return not self.succeeded

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id":    self.response_id,
            "request_id":     self.request_id,
            "operation":      self.operation,
            "order_id":       self.order_id,
            "succeeded":      self.succeeded,
            "failed":         self.failed,
            "error_message":  self.error_message,
            "error_code":     self.error_code,
            "responded_at":   self.responded_at,
            "duration_ms":    round(self.duration_ms, 2),
            "has_order":      self.managed_order is not None,
        }

    @classmethod
    def success(
        cls,
        request_id:    str,
        operation:     str,
        order_id:      str,
        managed_order: Optional[ManagedOrder] = None,
        *,
        duration_ms: float = 0.0,
        metadata:    dict[str, Any] | None = None,
    ) -> "OrderManagerResponse":
        return cls(
            request_id    = request_id,
            operation     = operation,
            order_id      = order_id,
            succeeded     = True,
            managed_order = managed_order,
            duration_ms   = duration_ms,
            metadata      = metadata or {},
        )

    @classmethod
    def failure(
        cls,
        request_id:    str,
        operation:     str,
        order_id:      str,
        error_message: str,
        *,
        error_code:  str = "",
        duration_ms: float = 0.0,
    ) -> "OrderManagerResponse":
        return cls(
            request_id    = request_id,
            operation     = operation,
            order_id      = order_id,
            succeeded     = False,
            error_message = error_message,
            error_code    = error_code,
            duration_ms   = duration_ms,
        )

    def __repr__(self) -> str:
        return (
            f"OrderManagerResponse("
            f"op={self.operation!r}, "
            f"order={self.order_id!r}, "
            f"ok={self.succeeded})"
        )
