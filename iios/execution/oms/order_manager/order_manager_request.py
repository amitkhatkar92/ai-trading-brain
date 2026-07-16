"""iios/execution/oms/order_manager/order_manager_request.py
==================================================
Request dataclasses for Order Manager operations.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from iios.execution.oms.order_manager.constants import (
    ManagerOrderState,
    OrderGroupType,
    OrderOwnership,
)

if TYPE_CHECKING:
    from iios.execution.lifecycle.order import Order


@dataclass
class OrderManagerRequest:
    """Base request for all Order Manager operations."""

    request_id:     str = field(default_factory=lambda: str(uuid.uuid4()))
    operation:      str = ""
    order_id:       str = ""
    requested_by:   str = "iios:system"
    requested_at:   float = field(default_factory=time.time)
    correlation_id: str = ""
    metadata:       dict[str, Any] = field(default_factory=dict)

    @property
    def age_sec(self) -> float:
        return time.time() - self.requested_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "operation":      self.operation,
            "order_id":       self.order_id,
            "requested_by":   self.requested_by,
            "requested_at":   self.requested_at,
            "correlation_id": self.correlation_id,
        }


@dataclass
class CreateOrderRequest(OrderManagerRequest):
    """Request to create and register a new ManagedOrder."""

    operation:       str = "CREATE_ORDER"
    workflow_id:     str = ""
    execution_id:    str = ""
    portfolio_id:    str = ""
    strategy_id:     str = ""
    decision_id:     str = ""
    ownership:       OrderOwnership = OrderOwnership.STRATEGY
    owner_id:        str = ""
    parent_order_id: str = ""
    group_id:        str = ""
    group_type:      Optional[OrderGroupType] = None
    tags:            frozenset[str] = field(default_factory=frozenset)
    notes:           str = ""
    order:           Optional[Any] = None   # M1 Order


@dataclass
class UpdateOrderRequest(OrderManagerRequest):
    """Request to update a managed order's OMS state."""

    operation:   str = "UPDATE_ORDER"
    new_state:   Optional[ManagerOrderState] = None
    reason:      str = ""
    actor:       str = "iios:system"
    error_message: str = ""
    error_code:  str = ""


@dataclass
class SuspendOrderRequest(OrderManagerRequest):
    """Request to suspend processing of a managed order."""

    operation: str = "SUSPEND_ORDER"
    reason:    str = ""


@dataclass
class ResumeOrderRequest(OrderManagerRequest):
    """Request to resume a suspended managed order."""

    operation: str = "RESUME_ORDER"
    reason:    str = ""


@dataclass
class CloseOrderRequest(OrderManagerRequest):
    """Request to close (complete) a managed order."""

    operation:     str = "CLOSE_ORDER"
    reason:        str = ""
    error_message: str = ""
    succeeded:     bool = True


@dataclass
class ArchiveOrderRequest(OrderManagerRequest):
    """Request to archive a completed/failed managed order."""

    operation: str = "ARCHIVE_ORDER"
    reason:    str = ""


@dataclass
class RemoveOrderRequest(OrderManagerRequest):
    """Request to permanently remove a managed order."""

    operation: str = "REMOVE_ORDER"
    reason:    str = ""


@dataclass
class LookupOrderRequest(OrderManagerRequest):
    """Request to look up a managed order."""

    operation: str = "LOOKUP_ORDER"
