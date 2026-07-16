"""iios/execution/oms/order_manager/order_manager_factory.py
==================================================
OrderManagerFactory — creates ManagedOrder objects.

IIOS v1.0: logging, audit.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import uuid
from typing import Any, Optional, TYPE_CHECKING

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_FACTORY,
    FACTORY_SYSTEM_ID,
    ManagerOrderState,
    OrderGroupType,
    OrderOwnership,
    VERSION,
)
from .order_manager_context import ManagedOrder
from .order_manager_request import CreateOrderRequest

if TYPE_CHECKING:
    from iios.execution.lifecycle.order import Order

_log   = get_logger(__name__, engine_id=FACTORY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=FACTORY_SYSTEM_ID,
                          component="OrderManagerFactory")


class OrderManagerFactory:
    """
    Factory that creates ManagedOrder objects from CreateOrderRequest.

    Stateless. Thread-safe.
    """

    def create(
        self,
        request: CreateOrderRequest,
    ) -> ManagedOrder:
        """Create a ManagedOrder from a CreateOrderRequest."""
        managed = ManagedOrder(
            order_id       = request.order_id,
            workflow_id    = request.workflow_id,
            execution_id   = request.execution_id,
            portfolio_id   = request.portfolio_id,
            strategy_id    = request.strategy_id,
            decision_id    = request.decision_id,
            correlation_id = request.correlation_id,
            order          = request.order,
            manager_state  = ManagerOrderState.READY,
            ownership      = request.ownership,
            owner_id       = request.owner_id,
            parent_order_id = request.parent_order_id,
            group_id       = request.group_id,
            group_type     = request.group_type,
            tags           = request.tags,
            notes          = request.notes,
        )
        _log.info("ManagedOrder created.", order_id=managed.order_id)
        _audit.log_workflow_event(
            FACTORY_SYSTEM_ID, "create", "MANAGED_ORDER_CREATED",
            actor    = ACTOR_FACTORY,
            order_id = managed.order_id,
        )
        return managed

    def create_from_params(
        self,
        order_id:        str,
        workflow_id:     str        = "",
        execution_id:    str        = "",
        portfolio_id:    str        = "",
        strategy_id:     str        = "",
        decision_id:     str        = "",
        correlation_id:  str        = "",
        order:           Optional[Any] = None,
        ownership:       OrderOwnership = OrderOwnership.STRATEGY,
        owner_id:        str        = "",
        parent_order_id: str        = "",
        group_id:        str        = "",
        group_type:      Optional[OrderGroupType] = None,
        tags:            frozenset[str] = frozenset(),
        notes:           str        = "",
    ) -> ManagedOrder:
        """Convenience: create a ManagedOrder directly from named parameters."""
        req = CreateOrderRequest(
            order_id        = order_id,
            workflow_id     = workflow_id,
            execution_id    = execution_id,
            portfolio_id    = portfolio_id,
            strategy_id     = strategy_id,
            decision_id     = decision_id,
            correlation_id  = correlation_id,
            order           = order,
            ownership       = ownership,
            owner_id        = owner_id,
            parent_order_id = parent_order_id,
            group_id        = group_id,
            group_type      = group_type,
            tags            = tags,
            notes           = notes,
        )
        return self.create(req)

    @staticmethod
    def gen_order_id(prefix: str = "ORD") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

    @staticmethod
    def gen_group_id(prefix: str = "GRP") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
