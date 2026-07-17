"""iios/execution/gateway/routing/routing_context.py
==================================================
RoutingContext — immutable input context for routing decisions.

Carries all execution metadata required by the routing engine
to evaluate policies and select a broker destination.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional

from iios.execution.gateway.brokers.constants import BrokerCapability


@dataclass(frozen=True)
class RoutingContext:
    """
    Immutable context for a single routing request.

    Contains execution metadata, instrument details, and policy hints.
    Never contains credentials, broker state, or execution outcomes.
    """

    # ── Correlation IDs ───────────────────────────────────────────────────────
    routing_id:   str
    execution_id: str
    order_id:     str
    portfolio_id: str
    strategy_id:  str

    # ── Instrument ────────────────────────────────────────────────────────────
    symbol:      str
    exchange:    str
    side:        str         # BUY / SELL
    order_type:  str         # MARKET / LIMIT / SL / SL_M
    product:     str         # MIS / CNC / NRML
    asset_class: str         # EQUITY / OPTIONS / FUTURES / CURRENCY / COMMODITY

    # ── Order attributes ──────────────────────────────────────────────────────
    quantity: float
    price:    float

    # ── Policy hints ──────────────────────────────────────────────────────────
    preferred_broker_id:    Optional[str]
    required_capabilities:  FrozenSet[BrokerCapability]
    priority:               int          # 0 = normal, > 0 = high priority

    # ── Timing ────────────────────────────────────────────────────────────────
    submitted_at: float

    # ── Extras ────────────────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_high_priority(self) -> bool:
        return self.priority > 0

    @property
    def has_preferred_broker(self) -> bool:
        return bool(self.preferred_broker_id)

    @property
    def has_required_capabilities(self) -> bool:
        return len(self.required_capabilities) > 0

    @property
    def age_ms(self) -> float:
        return (time.time() - self.submitted_at) * 1_000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "routing_id":           self.routing_id,
            "execution_id":         self.execution_id,
            "order_id":             self.order_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "symbol":               self.symbol,
            "exchange":             self.exchange,
            "side":                 self.side,
            "order_type":           self.order_type,
            "product":              self.product,
            "asset_class":          self.asset_class,
            "quantity":             self.quantity,
            "price":                self.price,
            "preferred_broker_id":  self.preferred_broker_id,
            "required_capabilities": sorted(c.value for c in self.required_capabilities),
            "priority":             self.priority,
            "submitted_at":         self.submitted_at,
            "metadata":             dict(self.metadata),
        }


# ── Factory function ──────────────────────────────────────────────────────────

def make_routing_context(
    execution_id: str,
    order_id:     str,
    portfolio_id: str,
    strategy_id:  str,
    *,
    symbol:      str = "",
    exchange:    str = "",
    side:        str = "BUY",
    order_type:  str = "MARKET",
    product:     str = "MIS",
    asset_class: str = "EQUITY",
    quantity:    float = 0.0,
    price:       float = 0.0,
    preferred_broker_id:   Optional[str]                        = None,
    required_capabilities: Optional[FrozenSet[BrokerCapability]] = None,
    priority:    int = 0,
    metadata:    Optional[Dict[str, Any]] = None,
) -> RoutingContext:
    """Create a RoutingContext with sensible defaults."""
    return RoutingContext(
        routing_id=str(uuid.uuid4()),
        execution_id=execution_id,
        order_id=order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        symbol=symbol,
        exchange=exchange,
        side=side,
        order_type=order_type,
        product=product,
        asset_class=asset_class,
        quantity=quantity,
        price=price,
        preferred_broker_id=preferred_broker_id,
        required_capabilities=required_capabilities or frozenset(),
        priority=priority,
        submitted_at=time.time(),
        metadata=dict(metadata or {}),
    )
