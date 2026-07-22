"""
portfolio_integration_context.py — iios.portfolio.integration
==============================================================
IntegrationContext — immutable per-request workflow context.

Carries all metadata needed to trace a request through the
integration workflow without mutating the original request.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    INTEGRATION_SYSTEM_ID,
    VERSION,
    IntegrationServiceType,
    WorkflowStage,
)


@dataclass(frozen=True)
class IntegrationContext:
    """
    Immutable per-request workflow context.

    Fields
    ------
    context_id :       Unique context identifier.
    request_id :       Associated request identifier.
    session_id :       Lifecycle session identifier (set after session init).
    portfolio_id :     Target portfolio identifier.
    service_type :     Requested service type.
    workflow_stage :   Current workflow stage.
    actor :            Requesting actor.
    correlation_id :   Optional external correlation ID for tracing.
    timestamp :        Context creation wall-clock time.
    metadata :         Supplementary context dict.
    framework_version: Framework version string.
    """
    context_id:        str
    request_id:        str
    session_id:        str
    portfolio_id:      str
    service_type:      str   # IntegrationServiceType.value
    workflow_stage:    str   # WorkflowStage.value
    actor:             str
    correlation_id:    str
    timestamp:         float
    metadata:          Dict[str, Any]
    framework_version: str

    @classmethod
    def create(
        cls,
        request_id:     str,
        portfolio_id:   str,
        service_type:   str,
        *,
        session_id:     str = "",
        actor:          str = INTEGRATION_SYSTEM_ID,
        correlation_id: str = "",
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "IntegrationContext":
        return cls(
            context_id        = str(uuid.uuid4()),
            request_id        = request_id,
            session_id        = session_id,
            portfolio_id      = portfolio_id,
            service_type      = service_type,
            workflow_stage    = WorkflowStage.REQUEST_RECEIVED.value,
            actor             = actor,
            correlation_id    = correlation_id,
            timestamp         = time.time(),
            metadata          = dict(metadata or {}),
            framework_version = VERSION,
        )

    def advance(self, stage: WorkflowStage) -> "IntegrationContext":
        """Return a new context advanced to the next workflow stage."""
        import dataclasses
        return dataclasses.replace(self, workflow_stage=stage.value)

    def with_session(self, session_id: str) -> "IntegrationContext":
        """Return a new context with the lifecycle session_id populated."""
        import dataclasses
        return dataclasses.replace(self, session_id=session_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":       self.context_id,
            "request_id":       self.request_id,
            "session_id":       self.session_id,
            "portfolio_id":     self.portfolio_id,
            "service_type":     self.service_type,
            "workflow_stage":   self.workflow_stage,
            "actor":            self.actor,
            "correlation_id":   self.correlation_id,
            "timestamp":        self.timestamp,
            "metadata":         dict(self.metadata),
            "framework_version": self.framework_version,
        }
