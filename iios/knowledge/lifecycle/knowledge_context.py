"""
knowledge_context.py — iios.knowledge.lifecycle
-------------------------------------------------
Context object that accompanies each lifecycle operation.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KnowledgeContext:
    """
    Immutable context block describing who triggered a lifecycle operation,
    when it was triggered, and any supplementary metadata.

    Fields
    ------
    context_id :   Unique context identifier.
    actor :        Identity that triggered the operation (system, user, etc.).
    triggered_at : Wall-clock time the operation was requested.
    correlation_id: Optional correlation token for tracing across systems.
    reason :        Human-readable reason for the operation.
    metadata :      Supplementary key-value metadata.
    """
    context_id:     str
    actor:          str
    triggered_at:   float          = field(default_factory=time.time)
    correlation_id: str            = ""
    reason:         str            = ""
    metadata:       Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        actor: str,
        *,
        context_id:     Optional[str]            = None,
        correlation_id: str                      = "",
        reason:         str                      = "",
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeContext":
        return cls(
            context_id     = context_id or str(uuid.uuid4()),
            actor          = actor,
            triggered_at   = time.time(),
            correlation_id = correlation_id,
            reason         = reason,
            metadata       = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "actor":          self.actor,
            "triggered_at":   self.triggered_at,
            "correlation_id": self.correlation_id,
            "reason":         self.reason,
        }
