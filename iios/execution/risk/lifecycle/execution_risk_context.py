"""iios/execution/risk/lifecycle/execution_risk_context.py
==================================================
RiskContext — immutable request-scoped context passed through
lifecycle operations.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class RiskContext:
    """
    Immutable context object that accompanies lifecycle requests.

    Carries all correlation and routing identifiers needed to trace
    a risk operation across the IIOS layer stack.
    """

    context_id:     str
    risk_id:        str
    execution_id:   str
    workflow_id:    str
    order_id:       str
    position_id:    str
    portfolio_id:   str
    strategy_id:    str
    decision_id:    str
    correlation_id: str
    requester:      str
    created_at:     float
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def age_ms(self) -> float:
        """Context age in milliseconds."""
        return (time.time() - self.created_at) * 1_000.0

    @property
    def has_order(self) -> bool:
        """True if an order_id is set."""
        return bool(self.order_id)

    @property
    def has_position(self) -> bool:
        """True if a position_id is set."""
        return bool(self.position_id)

    @property
    def has_decision(self) -> bool:
        """True if a decision_id is set."""
        return bool(self.decision_id)

    @property
    def has_workflow(self) -> bool:
        """True if a workflow_id is set."""
        return bool(self.workflow_id)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "context_id":     self.context_id,
            "risk_id":        self.risk_id,
            "execution_id":   self.execution_id,
            "workflow_id":    self.workflow_id,
            "order_id":       self.order_id,
            "position_id":    self.position_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "decision_id":    self.decision_id,
            "correlation_id": self.correlation_id,
            "requester":      self.requester,
            "created_at":     self.created_at,
            "metadata":       dict(self.metadata),
        }


def make_risk_context(
    *,
    risk_id:        str = "",
    execution_id:   str = "",
    workflow_id:    str = "",
    order_id:       str = "",
    position_id:    str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    decision_id:    str = "",
    correlation_id: str = "",
    requester:      str = "",
    metadata:       Dict[str, Any] | None = None,
) -> RiskContext:
    """Create a RiskContext with a fresh UUID and timestamp."""
    return RiskContext(
        context_id=str(uuid.uuid4()),
        risk_id=risk_id,
        execution_id=execution_id,
        workflow_id=workflow_id,
        order_id=order_id,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        decision_id=decision_id,
        correlation_id=correlation_id,
        requester=requester,
        created_at=time.time(),
        metadata=metadata or {},
    )
