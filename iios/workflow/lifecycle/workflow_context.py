"""
workflow_context.py — iios.workflow.lifecycle
----------------------------------------------
WorkflowContext — per-session operational context carrying
correlation and trace identifiers.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import FRAMEWORK_VERSION


@dataclass(frozen=True)
class WorkflowContext:
    """
    Immutable operational context for a workflow session.

    Carries correlation and trace identifiers that thread through the
    lifecycle for observability and audit purposes.
    """
    context_id:        str
    session_id:        str
    correlation_id:    str
    trace_id:          str
    environment:       str
    platform_metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        session_id:     str,
        *,
        correlation_id:    str = "",
        trace_id:          str = "",
        environment:       str = "production",
        platform_metadata: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowContext":
        return cls(
            context_id        = f"wctx-{uuid.uuid4().hex[:12]}",
            session_id        = session_id,
            correlation_id    = correlation_id or f"cid-{uuid.uuid4().hex[:8]}",
            trace_id          = trace_id or f"tid-{uuid.uuid4().hex[:8]}",
            environment       = environment,
            platform_metadata = dict(platform_metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "session_id":        self.session_id,
            "correlation_id":    self.correlation_id,
            "trace_id":          self.trace_id,
            "environment":       self.environment,
            "platform_metadata": self.platform_metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowContext":
        return cls(
            context_id        = d["context_id"],
            session_id        = d["session_id"],
            correlation_id    = d.get("correlation_id", ""),
            trace_id          = d.get("trace_id", ""),
            environment       = d.get("environment", "production"),
            platform_metadata = d.get("platform_metadata", {}),
        )
