"""iios/execution/core/execution_session.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.execution_constants import ExecutionStatus
from iios.execution.execution_exceptions import ExecutionStateError
from iios.execution.core.execution_request import ExecutionRequest
from iios.execution.core.execution_state import ExecutionState
from iios.execution.core.execution_plan import ExecutionPlan
from iios.execution.core.execution_result import ExecutionResult


@dataclass
class ExecutionSession:
    """
    Runtime container for a single end-to-end execution.

    Created when a request is submitted; holds the request, plan (once
    generated), state machine, all events, and the final result.
    """

    # ── Primary ID (externally visible) ──────────────────────────────────────
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ── Core payload ──────────────────────────────────────────────────────────
    request: ExecutionRequest = field(default_factory=ExecutionRequest)
    state:   ExecutionState   = field(default_factory=ExecutionState)

    # ── Lifecycle artifacts (populated as workflow progresses) ─────────────
    plan:   ExecutionPlan   | None = None
    result: ExecutionResult | None = None

    # ── Runtime tracking ──────────────────────────────────────────────────────
    retry_count: int   = 0
    max_retries: int   = 3

    # ── Timestamps ────────────────────────────────────────────────────────────
    started_at:    float       = field(default_factory=time.time)
    updated_at:    float       = field(default_factory=time.time)
    completed_at:  float | None = None

    # ── Events (lightweight list — full event stream lives in EventBus) ───────
    event_ids: list[str] = field(default_factory=list)

    # ── Extra ─────────────────────────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Keep state machine's execution_id in sync.
        if not self.state.execution_id:
            self.state.execution_id = self.execution_id

    # ── Convenience wrappers around state machine ──────────────────────────────

    @property
    def status(self) -> ExecutionStatus:
        return self.state.current_status

    def can_transition(self, target: ExecutionStatus) -> bool:
        return self.state.can_transition(target)

    def transition(self, target: ExecutionStatus, *, reason: str = "") -> None:
        self.state.transition(target, reason=reason)
        self.updated_at = time.time()
        if target in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.FAILED,
        ):
            self.completed_at = time.time()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    @property
    def is_active(self) -> bool:
        return self.state.is_active

    def add_event_id(self, event_id: str) -> None:
        self.event_ids.append(event_id)
        self.updated_at = time.time()

    def duration_ms(self) -> float:
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1_000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "status":       self.status.value,
            "request":      self.request.to_dict(),
            "state":        self.state.to_dict(),
            "plan":         self.plan.to_dict()   if self.plan   else None,
            "result":       self.result.to_dict() if self.result else None,
            "retry_count":  self.retry_count,
            "max_retries":  self.max_retries,
            "started_at":   self.started_at,
            "updated_at":   self.updated_at,
            "completed_at": self.completed_at,
            "event_ids":    list(self.event_ids),
            "metadata":     dict(self.metadata),
        }
