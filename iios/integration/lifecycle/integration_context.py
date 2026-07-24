"""
integration_context.py — iios.integration.lifecycle
-----------------------------------------------------
Per-session operational context carrying correlation and trace IDs.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import FRAMEWORK_VERSION


@dataclass(frozen=True)
class IntegrationContext:
    """
    Immutable operational context for an integration session.

    Carries correlation and trace identifiers that thread through the
    lifecycle for observability and audit purposes.
    """
    context_id:     str
    session_id:     str
    correlation_id: str
    trace_id:       str
    environment:    str
    metadata:       Dict[str, Any]

    @classmethod
    def create(
        cls,
        session_id:     str,
        *,
        correlation_id: str = "",
        trace_id:       str = "",
        environment:    str = "production",
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "IntegrationContext":
        return cls(
            context_id     = f"ictx-{uuid.uuid4().hex[:12]}",
            session_id     = session_id,
            correlation_id = correlation_id or f"cid-{uuid.uuid4().hex[:8]}",
            trace_id       = trace_id or f"tid-{uuid.uuid4().hex[:8]}",
            environment    = environment,
            metadata       = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "session_id":     self.session_id,
            "correlation_id": self.correlation_id,
            "trace_id":       self.trace_id,
            "environment":    self.environment,
            "metadata":       self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IntegrationContext":
        return cls(
            context_id     = d["context_id"],
            session_id     = d["session_id"],
            correlation_id = d.get("correlation_id", ""),
            trace_id       = d.get("trace_id", ""),
            environment    = d.get("environment", "production"),
            metadata       = d.get("metadata", {}),
        )
