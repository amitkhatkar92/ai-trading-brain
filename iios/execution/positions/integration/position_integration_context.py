"""iios/execution/positions/integration/position_integration_context.py
==================================================
IntegrationContext — immutable per-operation context carried
through the integration layer.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class IntegrationContext:
    """
    Immutable carrier of correlation and routing metadata for a
    single integration operation.

    Attributes
    ----------
    context_id
        Unique ID for this context instance.
    correlation_id
        External correlation ID (links to upstream request chain).
    portfolio_id
        Portfolio this operation belongs to.
    strategy_id
        Strategy this operation belongs to.
    workflow_id
        Workflow ID if triggered by a workflow.
    decision_id
        Decision ID if triggered by a decision.
    execution_id
        Execution ID if triggered by a broker execution.
    actor
        Who initiated the operation (human, system, strategy, etc.).
    created_at
        Unix timestamp when this context was created.
    metadata
        Arbitrary extra key-value pairs.
    """

    context_id:     str
    correlation_id: str  = ""
    portfolio_id:   str  = ""
    strategy_id:    str  = ""
    workflow_id:    str  = ""
    decision_id:    str  = ""
    execution_id:   str  = ""
    actor:          str  = ""
    created_at:     float = field(default_factory=time.time)
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "correlation_id": self.correlation_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "workflow_id":    self.workflow_id,
            "decision_id":    self.decision_id,
            "execution_id":   self.execution_id,
            "actor":          self.actor,
            "created_at":     self.created_at,
            "metadata":       dict(self.metadata),
        }


def make_integration_context(
    *,
    correlation_id: str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    workflow_id:    str = "",
    decision_id:    str = "",
    execution_id:   str = "",
    actor:          str = "",
    metadata:       Dict[str, Any] | None = None,
) -> IntegrationContext:
    """Factory that generates a fresh UUID context_id."""
    return IntegrationContext(
        context_id=str(uuid.uuid4()),
        correlation_id=correlation_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        workflow_id=workflow_id,
        decision_id=decision_id,
        execution_id=execution_id,
        actor=actor,
        metadata=metadata or {},
    )
