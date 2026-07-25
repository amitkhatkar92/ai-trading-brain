"""
workflow_context.py — iios.workflow.engine
-------------------------------------------
WorkflowEngineContext — per-request operational context for the engine.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import DEFAULT_ENGINE_ID, DEFAULT_ENVIRONMENT
from .workflow_request import WorkflowEngineRequest


@dataclass(frozen=True)
class WorkflowEngineContext:
    """
    Immutable per-request context threading correlation and trace IDs
    through the engine's coordination workflow.
    """
    context_id:       str
    request_id:       str
    session_id:       str
    engine_id:        str
    workflow_id:      str
    correlation_id:   str
    trace_id:         str
    environment:      str
    metadata:         Dict[str, Any]
    created_at:       str

    @classmethod
    def create(
        cls,
        request:    WorkflowEngineRequest,
        session_id: str,
        *,
        engine_id:  str                      = DEFAULT_ENGINE_ID,
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> "WorkflowEngineContext":
        return cls(
            context_id     = f"wenctx-{uuid.uuid4().hex[:12]}",
            request_id     = request.request_id,
            session_id     = session_id,
            engine_id      = engine_id,
            workflow_id    = request.workflow_id,
            correlation_id = request.correlation_id,
            trace_id       = request.trace_id,
            environment    = request.environment,
            metadata       = dict(metadata or {}),
            created_at     = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "request_id":     self.request_id,
            "session_id":     self.session_id,
            "engine_id":      self.engine_id,
            "workflow_id":    self.workflow_id,
            "correlation_id": self.correlation_id,
            "trace_id":       self.trace_id,
            "environment":    self.environment,
            "metadata":       self.metadata,
            "created_at":     self.created_at,
        }
