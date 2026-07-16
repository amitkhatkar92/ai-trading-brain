"""iios/execution/lifecycle/order_context.py
==================================================
OrderContext — immutable identifiers linking an order
to the strategy, portfolio, decision, and workflow
that produced it.

Context is frozen at order creation and never changes
during the order's lifetime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class OrderContext:
    """
    Immutable identifiers that trace the order back to its origin.

    Parameters
    ----------
    strategy_id : str
        Strategy that generated the order.
    portfolio_id : str
        Portfolio the order belongs to.
    decision_id : str
        Decision record that authorised this order.
    workflow_id : str
        InstitutionalWorkflowOrchestrator run that produced the decision.
    broker_id : str
        Target broker (empty string = not yet assigned).
    parent_order_id : str | None
        Parent order ID for child / split orders.  None for top-level.
    custom : dict[str, Any]
        Additional linkage metadata (read-only view returned via to_dict).
    """
    strategy_id:     str
    portfolio_id:    str
    decision_id:     str
    workflow_id:     str
    broker_id:       str            = ""
    parent_order_id: Optional[str]  = None
    custom:          dict[str, Any] = field(default_factory=dict)

    def with_broker(self, broker_id: str) -> "OrderContext":
        """Return a new OrderContext with broker_id set."""
        return OrderContext(
            strategy_id     = self.strategy_id,
            portfolio_id    = self.portfolio_id,
            decision_id     = self.decision_id,
            workflow_id     = self.workflow_id,
            broker_id       = broker_id,
            parent_order_id = self.parent_order_id,
            custom          = dict(self.custom),
        )

    def with_parent(self, parent_order_id: str) -> "OrderContext":
        """Return a new OrderContext with parent_order_id set."""
        return OrderContext(
            strategy_id     = self.strategy_id,
            portfolio_id    = self.portfolio_id,
            decision_id     = self.decision_id,
            workflow_id     = self.workflow_id,
            broker_id       = self.broker_id,
            parent_order_id = parent_order_id,
            custom          = dict(self.custom),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id":     self.strategy_id,
            "portfolio_id":    self.portfolio_id,
            "decision_id":     self.decision_id,
            "workflow_id":     self.workflow_id,
            "broker_id":       self.broker_id,
            "parent_order_id": self.parent_order_id,
            "custom":          dict(self.custom),
        }
