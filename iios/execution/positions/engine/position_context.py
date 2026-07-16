"""iios/execution/positions/engine/position_context.py
==================================================
EngineContext — immutable operation-scoped context carried through
all Position Engine requests.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import OperationType


@dataclass(frozen=True)
class EngineContext:
    """
    Immutable context for a single engine operation.

    Carries all correlation and routing identifiers needed to trace
    an operation across the IIOS layer stack.
    """

    context_id:     str
    operation_type: OperationType
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
        return (time.time() - self.created_at) * 1_000.0

    @property
    def has_workflow(self) -> bool:
        return bool(self.workflow_id)

    @property
    def has_execution(self) -> bool:
        return bool(self.execution_id)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "context_id":     self.context_id,
            "operation_type": self.operation_type.value,
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


def make_engine_context(
    operation_type: OperationType,
    *,
    portfolio_id:   str = "",
    strategy_id:    str = "",
    decision_id:    str = "",
    workflow_id:    str = "",
    execution_id:   str = "",
    correlation_id: str = "",
    requester:      str = "",
    metadata:       Dict[str, Any] | None = None,
) -> EngineContext:
    """Create an ``EngineContext`` with a fresh UUID and current timestamp."""
    return EngineContext(
        context_id=str(uuid.uuid4()),
        operation_type=operation_type,
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
