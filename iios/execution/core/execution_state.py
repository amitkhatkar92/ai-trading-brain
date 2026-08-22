"""iios/execution/core/execution_state.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.execution_constants import (
    VALID_TRANSITIONS,
    ExecutionStatus,
)
from iios.execution.execution_exceptions import ExecutionStateError


@dataclass
class StatusTransition:
    """Record of a single state-machine transition."""

    transition_id: str          = field(default_factory=lambda: str(uuid.uuid4()))
    from_status:   ExecutionStatus = ExecutionStatus.CREATED
    to_status:     ExecutionStatus = ExecutionStatus.CREATED
    timestamp:     float           = field(default_factory=time.time)
    reason:        str             = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_status":   self.from_status.value,
            "to_status":     self.to_status.value,
            "timestamp":     self.timestamp,
            "reason":        self.reason,
        }


@dataclass
class ExecutionState:
    """State machine for a single execution lifecycle."""

    execution_id:    str                    = ""
    current_status:  ExecutionStatus        = ExecutionStatus.CREATED
    previous_status: ExecutionStatus | None = None
    transitions:     list[StatusTransition] = field(default_factory=list)
    created_at:      float                  = field(default_factory=time.time)
    updated_at:      float                  = field(default_factory=time.time)

    # ── State machine ──────────────────────────────────────────────────────────

    def can_transition(self, target: ExecutionStatus) -> bool:
        return target in VALID_TRANSITIONS.get(self.current_status, [])

    def transition(self, target: ExecutionStatus, *, reason: str = "") -> None:
        if not self.can_transition(target):
            raise ExecutionStateError(
                f"Cannot transition {self.current_status.value!r} → {target.value!r}",
                from_status=self.current_status.value,
                to_status=target.value,
            )
        self.transitions.append(
            StatusTransition(
                from_status=self.current_status,
                to_status=target,
                timestamp=time.time(),
                reason=reason,
            )
        )
        self.previous_status = self.current_status
        self.current_status  = target
        self.updated_at      = time.time()

    @property
    def is_terminal(self) -> bool:
        from iios.execution.execution_constants import TERMINAL_STATUSES
        return self.current_status in TERMINAL_STATUSES

    @property
    def is_active(self) -> bool:
        from iios.execution.execution_constants import ACTIVE_STATUSES
        return self.current_status in ACTIVE_STATUSES

    def history(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.transitions]

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id":    self.execution_id,
            "current_status":  self.current_status.value,
            "previous_status": self.previous_status.value if self.previous_status else None,
            "transitions":     self.history(),
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
        }
