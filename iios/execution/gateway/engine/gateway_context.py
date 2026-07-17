"""iios/execution/gateway/engine/gateway_context.py
==================================================
EngineGatewayContext — immutable context carrying all input data
for a single submission to the Execution Gateway Engine.

Distinct from the M1 lifecycle GatewayContext.  This context carries
the full execution request including optional risk snapshot reference
and position data.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class EngineGatewayContext:
    """
    Immutable input context for a single engine submission.

    Carries all identifiers, execution attributes, optional risk data,
    and optional position data.  Created by the caller or via the
    ``make_engine_gateway_context()`` factory.

    This context is NOT mutated after creation.
    """

    # ── Required identifiers ──────────────────────────────────────────────────
    request_id:   str
    execution_id: str
    order_id:     str
    portfolio_id: str
    strategy_id:  str

    # ── Optional identifiers ──────────────────────────────────────────────────
    workflow_id:    str = ""
    position_id:    str = ""
    decision_id:    str = ""
    correlation_id: str = ""

    # ── Execution attributes ──────────────────────────────────────────────────
    symbol:     str   = ""
    side:       str   = ""       # BUY / SELL
    quantity:   float = 0.0
    price:      float = 0.0
    order_type: str   = ""       # MARKET / LIMIT / STOP / etc.
    asset_class: str  = ""       # EQUITY / OPTION / FUTURE / etc.

    # ── Risk data (from ExecutionRiskSnapshot — M4 M5) ────────────────────────
    risk_snapshot_id: str = ""
    risk_outcome:     str = ""   # PASSED / WARNING / BLOCKED / etc.
    risk_metadata:    Dict[str, Any] = field(default_factory=dict)

    # ── Position data (from PositionSnapshot) ─────────────────────────────────
    position_snapshot: Dict[str, Any] = field(default_factory=dict)

    # ── Execution payload (passed through; engine does not interpret) ─────────
    execution_payload: Dict[str, Any] = field(default_factory=dict)

    # ── Priority ──────────────────────────────────────────────────────────────
    priority: int = 0     # 0 = normal; higher value = higher priority

    # ── Timing ────────────────────────────────────────────────────────────────
    submitted_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_risk_data(self) -> bool:
        """True if a risk snapshot ID or outcome is present."""
        return bool(self.risk_snapshot_id or self.risk_outcome)

    @property
    def has_position_snapshot(self) -> bool:
        """True if position snapshot data is present."""
        return bool(self.position_snapshot)

    @property
    def has_execution_payload(self) -> bool:
        return bool(self.execution_payload)

    @property
    def is_high_priority(self) -> bool:
        return self.priority > 0

    @property
    def age_ms(self) -> float:
        """Milliseconds since this context was submitted."""
        return max(0.0, (time.time() - self.submitted_at) * 1_000.0)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
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
            "risk_snapshot_id":  self.risk_snapshot_id,
            "risk_outcome":      self.risk_outcome,
            "risk_metadata":     dict(self.risk_metadata),
            "position_snapshot": dict(self.position_snapshot),
            "execution_payload": dict(self.execution_payload),
            "priority":          self.priority,
            "submitted_at":      self.submitted_at,
        }


def make_engine_gateway_context(
    execution_id: str,
    order_id:     str,
    portfolio_id: str,
    strategy_id:  str,
    *,
    request_id: Optional[str] = None,
    **kw: Any,
) -> EngineGatewayContext:
    """
    Build an ``EngineGatewayContext`` from required identifiers.

    A ``request_id`` is auto-generated as a UUID if not supplied.
    All other fields from the dataclass may be passed as keyword arguments.
    """
    return EngineGatewayContext(
        request_id=request_id or str(uuid.uuid4()),
        execution_id=execution_id,
        order_id=order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        **kw,
    )
