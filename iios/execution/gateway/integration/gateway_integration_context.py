"""iios/execution/gateway/integration/gateway_integration_context.py
==================================================
GatewayIntegrationContext — immutable context for a single
integration workflow request.

Carries all the parameters needed to coordinate lifecycle,
routing, broker selection, and snapshot publication.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class GatewayIntegrationContext:
    """
    Immutable execution context for one gateway integration request.

    All required fields are positional-equivalent; all optional fields
    have sensible defaults.  Validation is performed by
    GatewayIntegrationValidator, not by this class.
    """

    # ── Required correlation IDs ───────────────────────────────────────────────
    execution_id:  str
    order_id:      str
    portfolio_id:  str
    strategy_id:   str

    # ── Instrument ────────────────────────────────────────────────────────────
    symbol:       str = ""
    exchange:     str = ""
    side:         str = "BUY"       # BUY | SELL
    order_type:   str = "MARKET"    # MARKET | LIMIT | ...
    product:      str = "MIS"       # MIS | CNC | NRML | ...
    asset_class:  str = "EQUITY"    # EQUITY | DERIVATIVE | ...
    quantity:     float = 0.0
    price:        float = 0.0

    # ── Optional routing hints ────────────────────────────────────────────────
    preferred_broker_id: Optional[str] = None
    routing_policy_id:   Optional[str] = None
    position_id:         Optional[str] = None
    workflow_id:         Optional[str] = None
    decision_id:         Optional[str] = None

    # ── Upstream snapshots (serialised, read-only) ────────────────────────────
    risk_snapshot:     Optional[Dict[str, Any]] = field(
        default=None, compare=False
    )
    position_snapshot: Optional[Dict[str, Any]] = field(
        default=None, compare=False
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: float = field(default_factory=time.time, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_buy(self) -> bool:
        return self.side.upper() == "BUY"

    @property
    def is_market_order(self) -> bool:
        return self.order_type.upper() == "MARKET"

    @property
    def has_preferred_broker(self) -> bool:
        return bool(self.preferred_broker_id)

    @property
    def has_routing_policy(self) -> bool:
        return bool(self.routing_policy_id)

    @property
    def has_risk_snapshot(self) -> bool:
        return self.risk_snapshot is not None

    @property
    def has_position_snapshot(self) -> bool:
        return self.position_snapshot is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id":        self.execution_id,
            "order_id":            self.order_id,
            "portfolio_id":        self.portfolio_id,
            "strategy_id":         self.strategy_id,
            "symbol":              self.symbol,
            "exchange":            self.exchange,
            "side":                self.side,
            "order_type":          self.order_type,
            "product":             self.product,
            "asset_class":         self.asset_class,
            "quantity":            self.quantity,
            "price":               self.price,
            "preferred_broker_id": self.preferred_broker_id,
            "routing_policy_id":   self.routing_policy_id,
            "position_id":         self.position_id,
            "workflow_id":         self.workflow_id,
            "decision_id":         self.decision_id,
            "has_risk_snapshot":   self.has_risk_snapshot,
            "has_position_snapshot": self.has_position_snapshot,
            "created_at":          self.created_at,
        }


def make_integration_context(
    execution_id: str,
    order_id:     str,
    portfolio_id: str,
    strategy_id:  str,
    *,
    symbol:       str = "",
    exchange:     str = "",
    side:         str = "BUY",
    order_type:   str = "MARKET",
    product:      str = "MIS",
    asset_class:  str = "EQUITY",
    quantity:     float = 0.0,
    price:        float = 0.0,
    preferred_broker_id: Optional[str] = None,
    routing_policy_id:   Optional[str] = None,
    position_id:         Optional[str] = None,
    workflow_id:         Optional[str] = None,
    decision_id:         Optional[str] = None,
    risk_snapshot:       Optional[Dict[str, Any]] = None,
    position_snapshot:   Optional[Dict[str, Any]] = None,
    metadata:            Optional[Dict[str, Any]] = None,
) -> GatewayIntegrationContext:
    return GatewayIntegrationContext(
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
        routing_policy_id=routing_policy_id,
        position_id=position_id,
        workflow_id=workflow_id,
        decision_id=decision_id,
        risk_snapshot=risk_snapshot,
        position_snapshot=position_snapshot,
        metadata=metadata or {},
    )
