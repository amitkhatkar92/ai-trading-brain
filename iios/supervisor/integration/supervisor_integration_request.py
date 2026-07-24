"""
supervisor_integration_request.py — iios.supervisor.integration
----------------------------------------------------------------
Immutable integration request value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationMode, VERSION
from .supervisor_integration_context import SupervisorIntegrationContext


@dataclass(frozen=True)
class SupervisorIntegrationRequest:
    """
    Immutable request for a single AI Supervisor Integration workflow cycle.

    The integration engine is the ONLY public entry point for the AI Supervisor
    & Autonomous Governance subsystem.  External components must construct a
    ``SupervisorIntegrationRequest`` and call
    :meth:`SupervisorIntegrationEngine.submit`.

    Fields
    ------
    request_id :      Unique request identifier.
    integration_id :  Integration run identifier.
    session_id :      Owning lifecycle session identifier.
    workflow_id :     Workflow routing identifier.
    mode :            Integration execution mode.
    context :         Extracted platform context.
    inputs :          Raw key-value input data (full platform snapshots).
    metadata :        Supplementary request metadata.
    requested_at :    Wall-clock creation time.
    framework_version: Framework version string.
    """
    request_id:        str
    integration_id:    str
    session_id:        str
    workflow_id:       str
    mode:              IntegrationMode
    context:           SupervisorIntegrationContext
    inputs:            Dict[str, Any] = field(default_factory=dict)
    metadata:          Dict[str, Any] = field(default_factory=dict)
    requested_at:      float          = field(default_factory=time.time)
    framework_version: str            = VERSION

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        integration_id: str,
        *,
        request_id:   Optional[str]                          = None,
        session_id:   str                                    = "",
        workflow_id:  str                                    = "",
        mode:         IntegrationMode                        = IntegrationMode.FULL,
        context:      Optional[SupervisorIntegrationContext] = None,
        inputs:       Optional[Dict[str, Any]]               = None,
        metadata:     Optional[Dict[str, Any]]               = None,
    ) -> "SupervisorIntegrationRequest":
        resolved_inputs = inputs or {}
        resolved_sid    = session_id or str(uuid.uuid4())
        resolved_wid    = workflow_id or str(uuid.uuid4())
        resolved_ctx    = context or SupervisorIntegrationContext.from_inputs(
            integration_id,
            resolved_inputs,
            session_id  = resolved_sid,
            workflow_id = resolved_wid,
            mode        = mode,
        )
        return cls(
            request_id     = request_id or str(uuid.uuid4()),
            integration_id = integration_id,
            session_id     = resolved_sid,
            workflow_id    = resolved_wid,
            mode           = mode,
            context        = resolved_ctx,
            inputs         = resolved_inputs,
            metadata       = metadata or {},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def with_inputs(self, extra: Dict[str, Any]) -> "SupervisorIntegrationRequest":
        """Return a new request with *extra* merged into inputs."""
        merged = {**self.inputs, **extra}
        return SupervisorIntegrationRequest(
            request_id        = self.request_id,
            integration_id    = self.integration_id,
            session_id        = self.session_id,
            workflow_id       = self.workflow_id,
            mode              = self.mode,
            context           = self.context,
            inputs            = merged,
            metadata          = self.metadata,
            requested_at      = self.requested_at,
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":      self.request_id,
            "integration_id":  self.integration_id,
            "session_id":      self.session_id,
            "workflow_id":     self.workflow_id,
            "mode":            self.mode.value,
            "requested_at":    self.requested_at,
            "framework_version": self.framework_version,
        }
