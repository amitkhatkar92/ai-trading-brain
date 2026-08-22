"""iios/execution/events/execution_event.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.execution_constants import ExecutionEventType


@dataclass
class ExecutionEvent:
    """
    Immutable event emitted during an execution lifecycle.

    Events flow through the EventBus and may be persisted or streamed
    to downstream consumers (monitoring, audit, notifications).
    """

    event_id:     str               = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str               = ""
    event_type:   ExecutionEventType = ExecutionEventType.CREATED
    timestamp:    float             = field(default_factory=time.time)

    # ── Context ───────────────────────────────────────────────────────────────
    source:  str             = ""    # e.g. "WorkflowEngine", "ExecutionManager"
    step:    str             = ""    # e.g. "validate", "execute"
    message: str             = ""
    details: dict[str, Any] = field(default_factory=dict)

    # ── Error information (for FAILED / STEP_FAILED events) ───────────────────
    error_code:    str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "execution_id":  self.execution_id,
            "event_type":    self.event_type.value,
            "timestamp":     self.timestamp,
            "source":        self.source,
            "step":          self.step,
            "message":       self.message,
            "details":       dict(self.details),
            "error_code":    self.error_code,
            "error_message": self.error_message,
        }
