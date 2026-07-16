"""iios/execution/oms/order_router/routing_context.py
==================================================
RoutingContext — immutable context for a single routing operation.

BrokerCapabilities — declares what a broker supports.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.oms.order_router.constants import (
    BrokerCapability,
    ExecutionMode,
    RoutingPolicyType,
)


@dataclass(frozen=True)
class BrokerCapabilities:
    """
    Declares the capabilities of a single named broker.

    Used by the router to determine whether a broker can
    handle a given order type, product type, and exchange.

    Never communicates with a broker — purely declarative.
    """
    broker_id:         str                          = ""
    display_name:      str                          = ""
    is_available:      bool                         = True
    supported_exchanges:   frozenset[str]           = field(default_factory=frozenset)
    supported_capabilities: frozenset[BrokerCapability] = field(default_factory=frozenset)
    supported_order_types:  frozenset[str]          = field(default_factory=frozenset)
    supported_product_types: frozenset[str]         = field(default_factory=frozenset)
    supported_execution_modes: frozenset[ExecutionMode] = field(default_factory=frozenset)
    priority:          int  = 0       # Higher = preferred
    latency_ms_est:    float = 0.0    # Estimated routing latency (informational)
    metadata:          dict[str, Any] = field(default_factory=dict)

    def supports_capability(self, cap: BrokerCapability) -> bool:
        return cap in self.supported_capabilities

    def supports_exchange(self, exchange: str) -> bool:
        return not self.supported_exchanges or exchange in self.supported_exchanges

    def supports_order_type(self, order_type: str) -> bool:
        return not self.supported_order_types or order_type in self.supported_order_types

    def supports_execution_mode(self, mode: ExecutionMode) -> bool:
        return not self.supported_execution_modes or mode in self.supported_execution_modes

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":          self.broker_id,
            "display_name":       self.display_name,
            "is_available":       self.is_available,
            "supported_exchanges": sorted(self.supported_exchanges),
            "supported_capabilities": [c.value for c in sorted(self.supported_capabilities, key=lambda x: x.value)],
            "priority":           self.priority,
            "latency_ms_est":     self.latency_ms_est,
        }


@dataclass(frozen=True)
class RoutingContext:
    """
    Immutable context for one routing operation.
    Carries all information needed to evaluate candidates.
    """
    context_id:     str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:       str = ""
    instrument:     str = ""
    exchange:       str = ""
    order_type:     str = ""
    side:           str = ""
    product_type:   str = ""
    workflow_id:    str = ""
    execution_id:   str = ""
    portfolio_id:   str = ""
    strategy_id:    str = ""
    execution_mode: ExecutionMode    = ExecutionMode.LIVE
    policy_type:    RoutingPolicyType = RoutingPolicyType.DEFAULT
    correlation_id: str = ""
    created_at:     float = field(default_factory=time.time)
    ttl_sec:        float = 60.0
    metadata:       dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_sec

    @property
    def is_paper(self) -> bool:
        return self.execution_mode in (ExecutionMode.PAPER, ExecutionMode.SIMULATION)

    @property
    def is_backtest(self) -> bool:
        return self.execution_mode == ExecutionMode.BACKTEST

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "order_id":       self.order_id,
            "instrument":     self.instrument,
            "exchange":       self.exchange,
            "order_type":     self.order_type,
            "side":           self.side,
            "product_type":   self.product_type,
            "execution_mode": self.execution_mode.value,
            "policy_type":    self.policy_type.value,
            "correlation_id": self.correlation_id,
            "created_at":     self.created_at,
            "is_expired":     self.is_expired,
        }
