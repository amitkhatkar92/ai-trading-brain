"""
knowledge_integration_context.py — iios.knowledge.integration
--------------------------------------------------------------
Context dataclasses for the Knowledge Integration module.

Provides:
    KnowledgeIntegrationContext  — per-execution context
    KnowledgeArtifactContext     — lightweight wrapper for input artifacts

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import FRAMEWORK_VERSION, IntegrationPhase


@dataclass(frozen=True)
class KnowledgeIntegrationContext:
    """
    Immutable per-execution context for a single integration operation.

    Created by the engine at the start of each submit() / query() / search() /
    retrieve() call.  Passed through all phases of the integration workflow.
    """
    integration_id:  str
    session_id:      str
    workflow_id:     str
    enterprise_id:   str
    correlation_id:  str
    trace_id:        str
    environment:     str
    phase:           IntegrationPhase
    started_at:      str
    metadata:        Dict[str, Any]

    @classmethod
    def create(
        cls,
        session_id:    str,
        workflow_id:   str,
        enterprise_id: str,
        *,
        environment:     str  = "production",
        correlation_id:  str  = "",
        trace_id:        str  = "",
        phase:           IntegrationPhase = IntegrationPhase.RECEIVE,
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeIntegrationContext":
        return cls(
            integration_id = f"intctx-{uuid.uuid4().hex[:12]}",
            session_id     = session_id,
            workflow_id    = workflow_id,
            enterprise_id  = enterprise_id,
            correlation_id = correlation_id or f"cid-{uuid.uuid4().hex[:8]}",
            trace_id       = trace_id or f"tid-{uuid.uuid4().hex[:8]}",
            environment    = environment,
            phase          = phase,
            started_at     = datetime.now(tz=timezone.utc).isoformat(),
            metadata       = dict(metadata or {}),
        )

    def with_phase(self, phase: IntegrationPhase) -> "KnowledgeIntegrationContext":
        """Return a new context with the updated phase."""
        return KnowledgeIntegrationContext(
            integration_id = self.integration_id,
            session_id     = self.session_id,
            workflow_id    = self.workflow_id,
            enterprise_id  = self.enterprise_id,
            correlation_id = self.correlation_id,
            trace_id       = self.trace_id,
            environment    = self.environment,
            phase          = phase,
            started_at     = self.started_at,
            metadata       = self.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_id": self.integration_id,
            "session_id":     self.session_id,
            "workflow_id":    self.workflow_id,
            "enterprise_id":  self.enterprise_id,
            "correlation_id": self.correlation_id,
            "trace_id":       self.trace_id,
            "environment":    self.environment,
            "phase":          self.phase.value,
            "started_at":     self.started_at,
            "metadata":       self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeIntegrationContext":
        return cls(
            integration_id = d["integration_id"],
            session_id     = d["session_id"],
            workflow_id    = d["workflow_id"],
            enterprise_id  = d["enterprise_id"],
            correlation_id = d.get("correlation_id", ""),
            trace_id       = d.get("trace_id", ""),
            environment    = d.get("environment", "production"),
            phase          = IntegrationPhase(d.get("phase", IntegrationPhase.RECEIVE.value)),
            started_at     = d.get("started_at", ""),
            metadata       = d.get("metadata", {}),
        )


@dataclass(frozen=True)
class KnowledgeArtifactContext:
    """
    Lightweight wrapper around an input artifact submitted for integration.
    """
    artifact_id:   str
    artifact_type: str
    source:        str
    content:       Dict[str, Any]

    @classmethod
    def create(
        cls,
        artifact_type: str,
        content:       Dict[str, Any],
        *,
        source:      str = "external",
        artifact_id: str = "",
    ) -> "KnowledgeArtifactContext":
        return cls(
            artifact_id   = artifact_id or f"art-{uuid.uuid4().hex[:10]}",
            artifact_type = artifact_type,
            source        = source,
            content       = dict(content),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id":   self.artifact_id,
            "artifact_type": self.artifact_type,
            "source":        self.source,
            "content":       self.content,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeArtifactContext":
        return cls(
            artifact_id   = d["artifact_id"],
            artifact_type = d["artifact_type"],
            source        = d.get("source", "external"),
            content       = d.get("content", {}),
        )
