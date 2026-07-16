"""iios/execution/context/execution_context_events.py
==================================================
ExecutionContextEvent and ExecutionContextEventType.

Events emitted by the Execution Context package at each
lifecycle transition.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from iios.execution.context.constants import ContextStatus, ExecutionMode


class ExecutionContextEventType(str, Enum):
    """Events emitted by the Execution Context lifecycle."""
    CONTEXT_CREATED    = "CONTEXT_CREATED"
    CONTEXT_VALIDATED  = "CONTEXT_VALIDATED"
    CONTEXT_PUBLISHED  = "CONTEXT_PUBLISHED"
    CONTEXT_REJECTED   = "CONTEXT_REJECTED"
    CONTEXT_ARCHIVED   = "CONTEXT_ARCHIVED"
    BUNDLE_CREATED     = "BUNDLE_CREATED"
    BUNDLE_PUBLISHED   = "BUNDLE_PUBLISHED"


@dataclass(frozen=True)
class ExecutionContextEvent:
    """Immutable event emitted by the Execution Context lifecycle."""

    event_id:       str                          = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:     ExecutionContextEventType    = ExecutionContextEventType.CONTEXT_CREATED
    context_id:     str                          = ""
    execution_id:   str                          = ""
    workflow_id:    str                          = ""
    occurred_at:    float                        = field(default_factory=time.time)
    execution_mode: Optional[ExecutionMode]      = None
    status:         Optional[ContextStatus]      = None
    error_message:  str                          = ""
    payload:        dict[str, Any]               = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "context_id":     self.context_id,
            "execution_id":   self.execution_id,
            "workflow_id":    self.workflow_id,
            "occurred_at":    self.occurred_at,
            "execution_mode": self.execution_mode.value if self.execution_mode else None,
            "status":         self.status.value         if self.status         else None,
            "error_message":  self.error_message,
            "payload":        self.payload,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionContextEvent("
            f"type={self.event_type.value}, "
            f"context={self.context_id[:8]}, "
            f"execution={self.execution_id[:8] if self.execution_id else '?'})"
        )


def make_context_event(
    event_type:    ExecutionContextEventType,
    context_id:    str,
    *,
    execution_id:  str = "",
    workflow_id:   str = "",
    execution_mode: Optional[ExecutionMode] = None,
    status:         Optional[ContextStatus] = None,
    error_message:  str = "",
    payload:        dict[str, Any] | None = None,
    occurred_at:    float = 0.0,
) -> ExecutionContextEvent:
    """Factory function for ExecutionContextEvent."""
    return ExecutionContextEvent(
        event_type     = event_type,
        context_id     = context_id,
        execution_id   = execution_id,
        workflow_id    = workflow_id,
        occurred_at    = occurred_at or time.time(),
        execution_mode = execution_mode,
        status         = status,
        error_message  = error_message,
        payload        = payload or {},
    )
