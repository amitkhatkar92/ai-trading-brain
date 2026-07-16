"""iios/execution/context/execution_bundle.py
==================================================
ExecutionBundle — an immutable group of related ExecutionContext objects.

Bundles arise when a single workflow generates multiple correlated
executions (e.g. bracket orders, basket orders, strategy rebalances).

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator

from iios.execution.context.constants import ExecutionMode, ContextStatus
from iios.execution.context.execution_context import ExecutionContext


@dataclass(frozen=True)
class ExecutionBundle:
    """
    Immutable collection of related ExecutionContext objects.

    A bundle shares a common workflow_id and execution_mode.
    All contained contexts must belong to the same workflow.
    """

    bundle_id:      str                          = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id:    str                          = ""
    execution_mode: ExecutionMode                = ExecutionMode.PAPER
    contexts:       tuple["ExecutionContext", ...] = field(default_factory=tuple)

    created_at:     float                        = field(default_factory=time.time)
    correlation_id: str                          = ""
    tags:           frozenset[str]               = field(default_factory=frozenset)
    metadata:       dict[str, Any]               = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return len(self.contexts)

    @property
    def is_empty(self) -> bool:
        return self.size == 0

    @property
    def context_ids(self) -> tuple[str, ...]:
        return tuple(c.context_id for c in self.contexts)

    @property
    def execution_ids(self) -> tuple[str, ...]:
        return tuple(c.execution_id for c in self.contexts)

    @property
    def order_ids(self) -> tuple[str, ...]:
        return tuple(c.order_id for c in self.contexts)

    @property
    def avg_completeness(self) -> float:
        if not self.contexts:
            return 0.0
        return sum(c.completeness for c in self.contexts) / self.size

    @property
    def all_validated(self) -> bool:
        return all(
            c.status == ContextStatus.VALIDATED
            for c in self.contexts
        )

    @property
    def all_published(self) -> bool:
        return all(
            c.status == ContextStatus.PUBLISHED
            for c in self.contexts
        )

    # ── Iteration ─────────────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[ExecutionContext]:
        return iter(self.contexts)

    def __len__(self) -> int:
        return self.size

    def __contains__(self, context_id: str) -> bool:
        return context_id in self.context_ids

    def get(self, context_id: str) -> ExecutionContext | None:
        for c in self.contexts:
            if c.context_id == context_id:
                return c
        return None

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id":        self.bundle_id,
            "workflow_id":      self.workflow_id,
            "execution_mode":   self.execution_mode.value,
            "size":             self.size,
            "context_ids":      list(self.context_ids),
            "execution_ids":    list(self.execution_ids),
            "order_ids":        list(self.order_ids),
            "avg_completeness": round(self.avg_completeness, 4),
            "all_validated":    self.all_validated,
            "all_published":    self.all_published,
            "created_at":       self.created_at,
            "correlation_id":   self.correlation_id,
            "tags":             sorted(self.tags),
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionBundle("
            f"id={self.bundle_id[:8]}, "
            f"workflow={self.workflow_id[:8] if self.workflow_id else '?'}, "
            f"size={self.size})"
        )
