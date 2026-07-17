"""iios/execution/gateway/lifecycle/gateway_context.py
==================================================
GatewayContext — immutable execution context that accompanies a
gateway request through its lifecycle.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class GatewayContext:
    """
    Immutable execution context for a gateway request.

    Contains the execution data that arrives at the gateway and is
    propagated through lifecycle stages.  The context never changes
    after creation — it represents the input as received.

    This is NOT a risk context and NOT a broker context.
    It ONLY carries execution identifiers and optional input data.
    """

    # ── Core identifiers ──────────────────────────────────────────────────────
    execution_id:  str
    order_id:      str
    portfolio_id:  str
    strategy_id:   str
    workflow_id:   str           = ""
    position_id:   str           = ""
    decision_id:   str           = ""
    correlation_id: str          = ""

    # ── Execution attributes ──────────────────────────────────────────────────
    symbol:        str           = ""
    side:          str           = ""         # BUY / SELL
    quantity:      float         = 0.0
    price:         float         = 0.0
    order_type:    str           = ""         # MARKET / LIMIT / etc.
    asset_class:   str           = ""         # EQUITY / OPTION / etc.

    # ── Optional payload (passed through; gateway does not interpret these) ──
    execution_payload: Dict[str, Any] = field(default_factory=dict)
    risk_metadata:     Dict[str, Any] = field(default_factory=dict)

    # ── Timing ────────────────────────────────────────────────────────────────
    received_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_execution_payload(self) -> bool:
        return bool(self.execution_payload)

    @property
    def has_risk_metadata(self) -> bool:
        return bool(self.risk_metadata)

    @property
    def age_ms(self) -> float:
        """Milliseconds since this context was created."""
        return max(0.0, (time.time() - self.received_at) * 1_000.0)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id":      self.execution_id,
            "order_id":          self.order_id,
            "portfolio_id":      self.portfolio_id,
            "strategy_id":       self.strategy_id,
            "workflow_id":       self.workflow_id,
            "position_id":       self.position_id,
            "decision_id":       self.decision_id,
            "correlation_id":    self.correlation_id,
            "symbol":            self.symbol,
            "side":              self.side,
            "quantity":          self.quantity,
            "price":             self.price,
            "order_type":        self.order_type,
            "asset_class":       self.asset_class,
            "execution_payload": dict(self.execution_payload),
            "risk_metadata":     dict(self.risk_metadata),
            "received_at":       self.received_at,
        }


def make_gateway_context(
    execution_id: str,
    order_id:     str,
    portfolio_id: str,
    strategy_id:  str,
    **kw: Any,
) -> GatewayContext:
    """
    Build a ``GatewayContext`` from required identifiers and optional keyword
    overrides.

    ``execution_id``, ``order_id``, ``portfolio_id``, and ``strategy_id`` are
    required.  All other ``GatewayContext`` fields may be supplied via ``kw``.
    """
    return GatewayContext(
        execution_id=execution_id,
        order_id=order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        **kw,
    )
