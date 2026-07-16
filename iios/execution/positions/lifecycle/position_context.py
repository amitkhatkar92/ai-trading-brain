"""iios/execution/positions/lifecycle/position_context.py
==================================================
PositionContext — immutable request-scoped context passed through
lifecycle operations.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class PositionContext:
    """
    Immutable context object that accompanies lifecycle requests.

    Carries all correlation and routing identifiers needed to trace
    a position operation across the IIOS layer stack.
    """

    context_id:     str
    portfolio_id:   str
    strategy_id:    str
    decision_id:    str
    workflow_id:    str
    execution_id:   str
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
    def has_workflow(self) -> bool:
        return bool(self.workflow_id)

    @property
    def has_decision(self) -> bool:
        return bool(self.decision_id)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "context_id":     self.context_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "decision_id":    self.decision_id,
            "workflow_id":    self.workflow_id,
            "execution_id":   self.execution_id,
            "correlation_id": self.correlation_id,
            "requester":      self.requester,
            "created_at":     self.created_at,
            "metadata":       dict(self.metadata),
        }


def make_context(
    *,
    portfolio_id:   str = "",
    strategy_id:    str = "",
    decision_id:    str = "",
    workflow_id:    str = "",
    execution_id:   str = "",
    correlation_id: str = "",
    requester:      str = "",
    metadata:       Dict[str, Any] | None = None,
) -> PositionContext:
    """Create a PositionContext with a fresh UUID and timestamp."""
    return PositionContext(
        context_id=str(uuid.uuid4()),
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        decision_id=decision_id,
        workflow_id=workflow_id,
        execution_id=execution_id,
        correlation_id=correlation_id,
        requester=requester,
        created_at=time.time(),
        metadata=metadata or {},
    )
