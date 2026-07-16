"""iios/execution/oms/order_router/routing_request.py
==================================================
RoutingRequest — input to the routing engine.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.oms.order_router.constants import (
    ExecutionMode,
    RoutingPolicyType,
)
from iios.execution.oms.order_router.routing_context import (
    BrokerCapabilities,
    RoutingContext,
)


@dataclass
class RoutingRequest:
    """
    Mutable request object submitted to the OrderRouter.

    Carries everything the router needs to determine the
    optimal routing target — never contains execution logic.
    """
    order_id:       str  = ""
    instrument:     str  = ""
    exchange:       str  = ""
    order_type:     str  = ""
    side:           str  = ""
    product_type:   str  = ""
    quantity:       float = 0.0
    price:          float = 0.0
    workflow_id:    str  = ""
    execution_id:   str  = ""
    portfolio_id:   str  = ""
    strategy_id:    str  = ""
    decision_id:    str  = ""
    correlation_id: str  = ""

    execution_mode:  ExecutionMode    = ExecutionMode.LIVE
    policy_type:     RoutingPolicyType = RoutingPolicyType.DEFAULT

    # Broker candidates the caller wants to consider (empty = all registered)
    candidate_broker_ids: list[str]  = field(default_factory=list)

    # Pre-resolved capabilities (optional; if empty, registry is consulted)
    broker_capabilities: list[BrokerCapabilities] = field(default_factory=list)

    request_id:  str   = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:  float = field(default_factory=time.time)
    ttl_sec:     float = 60.0

    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_sec

    def build_context(self) -> RoutingContext:
        """Produce an immutable RoutingContext from this request."""
        return RoutingContext(
            order_id       = self.order_id,
            instrument     = self.instrument,
            exchange       = self.exchange,
            order_type     = self.order_type,
            side           = self.side,
            product_type   = self.product_type,
            workflow_id    = self.workflow_id,
            execution_id   = self.execution_id,
            portfolio_id   = self.portfolio_id,
            strategy_id    = self.strategy_id,
            execution_mode = self.execution_mode,
            policy_type    = self.policy_type,
            correlation_id = self.correlation_id,
            created_at     = self.created_at,
            ttl_sec        = self.ttl_sec,
            metadata       = dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "order_id":       self.order_id,
            "instrument":     self.instrument,
            "exchange":       self.exchange,
            "order_type":     self.order_type,
            "side":           self.side,
            "product_type":   self.product_type,
            "quantity":       self.quantity,
            "execution_mode": self.execution_mode.value,
            "policy_type":    self.policy_type.value,
            "workflow_id":    self.workflow_id,
            "execution_id":   self.execution_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "created_at":     self.created_at,
            "is_expired":     self.is_expired,
        }
