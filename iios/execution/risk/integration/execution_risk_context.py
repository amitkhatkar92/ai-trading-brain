"""iios/execution/risk/integration/execution_risk_context.py
==================================================
ExecutionContext — immutable input context for an integration evaluation.

This is the integration-layer context object.  It is independent of
M2's EvaluationContext (which is internal to the risk engine).

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class ExecutionContext:
    """
    Immutable context describing the execution for which risk is being evaluated.

    Carries all identifiers, snapshots, and limits the integration engine
    needs to coordinate the risk workflow.
    """

    # ── Execution identifiers ─────────────────────────────────────────────────
    execution_id:   str
    order_id:       str
    position_id:    str = ""
    portfolio_id:   str = ""
    strategy_id:    str = ""
    workflow_id:    str = ""
    decision_id:    str = ""
    correlation_id: str = ""

    # ── Instrument & order details ────────────────────────────────────────────
    symbol:     str   = ""
    side:       str   = ""    # "BUY" | "SELL"
    quantity:   float = 0.0
    price:      float = 0.0
    order_type: str   = ""    # "MARKET" | "LIMIT" | "STOP" | …
    asset_class: str  = ""    # "EQUITY" | "OPTION" | "FUTURE" | …

    # ── Timestamp ─────────────────────────────────────────────────────────────
    timestamp: float = field(default_factory=time.time)

    # ── External data snapshots passed verbatim to rules ─────────────────────
    execution_snapshot: Dict[str, Any] = field(default_factory=dict, compare=False)
    position_snapshot:  Dict[str, Any] = field(default_factory=dict, compare=False)
    risk_limits:        Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Arbitrary metadata ────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_execution_snapshot(self) -> bool:
        return bool(self.execution_snapshot)

    @property
    def has_position_snapshot(self) -> bool:
        return bool(self.position_snapshot)

    @property
    def has_risk_limits(self) -> bool:
        return bool(self.risk_limits)

    @property
    def age_ms(self) -> float:
        return (time.time() - self.timestamp) * 1_000.0

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id":         self.execution_id,
            "order_id":             self.order_id,
            "position_id":          self.position_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "workflow_id":          self.workflow_id,
            "decision_id":          self.decision_id,
            "correlation_id":       self.correlation_id,
            "symbol":               self.symbol,
            "side":                 self.side,
            "quantity":             self.quantity,
            "price":                self.price,
            "order_type":           self.order_type,
            "asset_class":          self.asset_class,
            "timestamp":            self.timestamp,
            "has_execution_snapshot": self.has_execution_snapshot,
            "has_position_snapshot":  self.has_position_snapshot,
            "has_risk_limits":      self.has_risk_limits,
            "metadata":             dict(self.metadata),
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_execution_context(
    execution_id: str,
    order_id:     str,
    *,
    position_id:    str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    workflow_id:    str = "",
    decision_id:    str = "",
    correlation_id: str = "",
    symbol:         str = "",
    side:           str = "",
    quantity:       float = 0.0,
    price:          float = 0.0,
    order_type:     str = "",
    asset_class:    str = "",
    execution_snapshot: Dict[str, Any] | None = None,
    position_snapshot:  Dict[str, Any] | None = None,
    risk_limits:        Dict[str, Any] | None = None,
    metadata:           Dict[str, Any] | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        execution_id=execution_id,
        order_id=order_id,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        workflow_id=workflow_id,
        decision_id=decision_id,
        correlation_id=correlation_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        order_type=order_type,
        asset_class=asset_class,
        execution_snapshot=execution_snapshot or {},
        position_snapshot=position_snapshot or {},
        risk_limits=risk_limits or {},
        metadata=metadata or {},
    )
