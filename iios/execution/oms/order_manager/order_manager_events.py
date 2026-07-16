"""iios/execution/oms/order_manager/order_manager_events.py
==================================================
Events emitted by the Order Manager lifecycle.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.oms.order_manager.constants import (
    ManagerEventType,
    ManagerOrderState,
)


@dataclass(frozen=True)
class OrderManagerEvent:
    """Immutable event emitted by the Order Manager."""

    event_id:      str               = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:    ManagerEventType  = ManagerEventType.ORDER_REGISTERED
    order_id:      str               = ""
    workflow_id:   str               = ""
    manager_state: Optional[ManagerOrderState] = None
    occurred_at:   float             = field(default_factory=time.time)
    actor:         str               = "iios:system"
    reason:        str               = ""
    error_message: str               = ""
    payload:       dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "event_type":    self.event_type.value,
            "order_id":      self.order_id,
            "workflow_id":   self.workflow_id,
            "manager_state": self.manager_state.value if self.manager_state else None,
            "occurred_at":   self.occurred_at,
            "actor":         self.actor,
            "reason":        self.reason,
            "error_message": self.error_message,
            "payload":       self.payload,
        }

    def __repr__(self) -> str:
        return (
            f"OrderManagerEvent(type={self.event_type.value}, "
            f"order={self.order_id!r})"
        )


def make_manager_event(
    event_type:    ManagerEventType,
    order_id:      str = "",
    *,
    workflow_id:   str = "",
    manager_state: Optional[ManagerOrderState] = None,
    actor:         str = "iios:system",
    reason:        str = "",
    error_message: str = "",
    payload:       dict[str, Any] | None = None,
    occurred_at:   float = 0.0,
) -> OrderManagerEvent:
    """Factory function for OrderManagerEvent."""
    return OrderManagerEvent(
        event_type    = event_type,
        order_id      = order_id,
        workflow_id   = workflow_id,
        manager_state = manager_state,
        occurred_at   = occurred_at or time.time(),
        actor         = actor,
        reason        = reason,
        error_message = error_message,
        payload       = payload or {},
    )
