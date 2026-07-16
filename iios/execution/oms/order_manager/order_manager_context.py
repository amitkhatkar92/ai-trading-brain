"""iios/execution/oms/order_manager/order_manager_context.py
==================================================
ManagedOrder — the core OMS entity that wraps an M1 Order
with manager-level state, ownership, and relationship data.

OrderManagerSnapshot — point-in-time summary of the manager.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional, TYPE_CHECKING

from iios.execution.oms.order_manager.constants import (
    ManagerOrderState,
    OrderGroupType,
    OrderOwnership,
    VERSION,
)

if TYPE_CHECKING:
    from iios.execution.lifecycle.order import Order


@dataclass
class ManagedOrder:
    """
    OMS wrapper around an M1 Order.

    Tracks the OMS coordination lifecycle, ownership, parent-child
    relationships, group membership, and processing metadata.

    This is the primary object produced and managed by the Order Manager.
    """

    # ── Core identity ─────────────────────────────────────────────────────────
    managed_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:      str   = ""
    workflow_id:   str   = ""
    execution_id:  str   = ""
    portfolio_id:  str   = ""
    strategy_id:   str   = ""
    decision_id:   str   = ""
    correlation_id: str  = ""

    # ── The underlying M1 Order ───────────────────────────────────────────────
    order: Optional[Any] = None    # iios.execution.lifecycle.order.Order

    # ── OMS state ─────────────────────────────────────────────────────────────
    manager_state: ManagerOrderState = ManagerOrderState.INITIALIZED

    # ── Ownership ─────────────────────────────────────────────────────────────
    ownership:     OrderOwnership = OrderOwnership.STRATEGY
    owner_id:      str            = ""    # strategy_id or user_id of the owner

    # ── Relationships ─────────────────────────────────────────────────────────
    parent_order_id:  str             = ""
    child_order_ids:  tuple[str, ...] = field(default_factory=tuple)
    group_id:         str             = ""
    group_type:       Optional[OrderGroupType] = None

    # ── Timing ────────────────────────────────────────────────────────────────
    registered_at:  float          = field(default_factory=time.time)
    processing_started_at: Optional[float] = None
    completed_at:   Optional[float] = None

    # ── Suspension ────────────────────────────────────────────────────────────
    is_suspended:   bool  = False
    suspend_reason: str   = ""

    # ── Error tracking ────────────────────────────────────────────────────────
    error_message:  str   = ""
    error_code:     str   = ""
    error_count:    int   = 0

    # ── Metadata ──────────────────────────────────────────────────────────────
    tags:           frozenset[str]  = field(default_factory=frozenset)
    notes:          str             = ""
    metadata:       dict[str, Any]  = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_terminal(self) -> bool:
        from iios.execution.oms.order_manager.constants import TERMINAL_MANAGER_STATES
        return self.manager_state in TERMINAL_MANAGER_STATES

    @property
    def is_active(self) -> bool:
        from iios.execution.oms.order_manager.constants import ACTIVE_MANAGER_STATES
        return self.manager_state in ACTIVE_MANAGER_STATES

    @property
    def is_completed(self) -> bool:
        return self.manager_state == ManagerOrderState.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.manager_state == ManagerOrderState.FAILED

    @property
    def has_parent(self) -> bool:
        return bool(self.parent_order_id)

    @property
    def has_children(self) -> bool:
        return bool(self.child_order_ids)

    @property
    def is_in_group(self) -> bool:
        return bool(self.group_id)

    @property
    def child_count(self) -> int:
        return len(self.child_order_ids)

    @property
    def processing_time_ms(self) -> Optional[float]:
        if self.processing_started_at is None:
            return None
        end = self.completed_at or time.time()
        return (end - self.processing_started_at) * 1_000

    @property
    def order_state(self) -> str:
        """Current M1 OrderState of the underlying order (if available)."""
        if self.order is not None and hasattr(self.order, "state"):
            return self.order.state.value
        return ""

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def add_child(self, child_order_id: str) -> None:
        if child_order_id not in self.child_order_ids:
            self.child_order_ids = self.child_order_ids + (child_order_id,)

    def remove_child(self, child_order_id: str) -> None:
        self.child_order_ids = tuple(
            cid for cid in self.child_order_ids if cid != child_order_id
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "managed_id":        self.managed_id,
            "order_id":          self.order_id,
            "workflow_id":       self.workflow_id,
            "execution_id":      self.execution_id,
            "portfolio_id":      self.portfolio_id,
            "strategy_id":       self.strategy_id,
            "decision_id":       self.decision_id,
            "correlation_id":    self.correlation_id,
            "manager_state":     self.manager_state.value,
            "order_state":       self.order_state,
            "ownership":         self.ownership.value,
            "owner_id":          self.owner_id,
            "parent_order_id":   self.parent_order_id,
            "child_order_ids":   list(self.child_order_ids),
            "group_id":          self.group_id,
            "group_type":        self.group_type.value if self.group_type else None,
            "is_terminal":       self.is_terminal,
            "is_active":         self.is_active,
            "is_suspended":      self.is_suspended,
            "suspend_reason":    self.suspend_reason,
            "error_message":     self.error_message,
            "error_count":       self.error_count,
            "registered_at":     self.registered_at,
            "processing_time_ms": self.processing_time_ms,
            "tags":              sorted(self.tags),
            "notes":             self.notes,
        }

    def __repr__(self) -> str:
        return (
            f"ManagedOrder("
            f"order_id={self.order_id!r}, "
            f"state={self.manager_state.value}, "
            f"children={self.child_count})"
        )


@dataclass(frozen=True)
class OrderManagerSnapshot:
    """
    Immutable point-in-time summary of the Order Manager's state.
    Published at significant lifecycle moments.
    """
    snapshot_id:      str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version:   str = VERSION
    captured_at:      float = field(default_factory=time.time)

    # Counts
    total_registered: int = 0
    active_count:     int = 0
    completed_count:  int = 0
    failed_count:     int = 0
    suspended_count:  int = 0

    # Peak
    peak_active:      int = 0

    # Metadata
    manager_running:  bool = False
    metadata:         dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":      self.snapshot_id,
            "schema_version":   self.schema_version,
            "captured_at":      self.captured_at,
            "total_registered": self.total_registered,
            "active_count":     self.active_count,
            "completed_count":  self.completed_count,
            "failed_count":     self.failed_count,
            "suspended_count":  self.suspended_count,
            "peak_active":      self.peak_active,
            "manager_running":  self.manager_running,
        }
