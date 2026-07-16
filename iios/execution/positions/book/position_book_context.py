"""iios/execution/positions/book/position_book_context.py
==================================================
BookContext — operation context for Position Book actions.

make_book_context() — factory function.

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ACTOR_BOOK, BookOperationType


@dataclass(frozen=True)
class BookContext:
    """
    Immutable context record attached to a single book operation.

    Carries correlation, actor, and optional workflow/execution IDs
    for end-to-end tracing across the system.
    """

    context_id:     str
    operation_type: BookOperationType
    portfolio_id:   str
    strategy_id:    str
    correlation_id: str
    requester:      str
    workflow_id:    str
    execution_id:   str
    created_at:     float
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def age_ms(self) -> float:
        """Elapsed milliseconds since this context was created."""
        return (time.time() - self.created_at) * 1_000

    @property
    def has_workflow(self) -> bool:
        return bool(self.workflow_id)

    @property
    def has_execution(self) -> bool:
        return bool(self.execution_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "operation_type": self.operation_type.value,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "correlation_id": self.correlation_id,
            "requester":      self.requester,
            "workflow_id":    self.workflow_id,
            "execution_id":   self.execution_id,
            "created_at":     self.created_at,
        }


def make_book_context(
    operation_type: BookOperationType,
    *,
    portfolio_id:   str = "",
    strategy_id:    str = "",
    correlation_id: str = "",
    requester:      str = ACTOR_BOOK,
    workflow_id:    str = "",
    execution_id:   str = "",
    metadata:       Optional[Dict[str, Any]] = None,
) -> BookContext:
    """Factory for ``BookContext`` with a generated UUID and current timestamp."""
    return BookContext(
        context_id=str(uuid.uuid4()),
        operation_type=operation_type,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        correlation_id=correlation_id,
        requester=requester,
        workflow_id=workflow_id,
        execution_id=execution_id,
        created_at=time.time(),
        metadata=metadata or {},
    )
