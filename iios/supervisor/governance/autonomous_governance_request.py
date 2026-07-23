"""
autonomous_governance_request.py — iios.supervisor.governance
--------------------------------------------------------------
Immutable governance assessment request value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import VERSION, SupervisionDomain
from .autonomous_governance_context import AutonomousGovernanceContext


@dataclass(frozen=True)
class AutonomousGovernanceRequest:
    """
    Immutable request for a single autonomous governance assessment cycle.

    Fields
    ------
    request_id :        Unique request identifier.
    supervision_id :    Supervision run identifier.
    subsystem_id :      Target subsystem identifier.
    workflow_type :     Workflow classification string.
    domains :           Supervision domains in scope for this cycle.
    context :           Full enterprise context snapshot.
    inputs :            Raw key-value extras.
    requested_at :      Wall-clock request creation time.
    metadata :          Supplementary request metadata.
    framework_version : Framework version string.
    """
    request_id:        str
    supervision_id:    str
    subsystem_id:      str
    workflow_type:     str
    domains:           tuple                   # Tuple[SupervisionDomain, ...]
    context:           AutonomousGovernanceContext
    inputs:            Dict[str, Any]          = field(default_factory=dict)
    requested_at:      float                   = field(default_factory=time.time)
    metadata:          Dict[str, Any]          = field(default_factory=dict)
    framework_version: str                     = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        subsystem_id:   str = "",
        workflow_type:  str = "enterprise_health_review",
        *,
        request_id: Optional[str]                          = None,
        domains:    Optional[List[SupervisionDomain]]      = None,
        context:    Optional[AutonomousGovernanceContext]  = None,
        inputs:     Optional[Dict[str, Any]]               = None,
        metadata:   Optional[Dict[str, Any]]               = None,
    ) -> "AutonomousGovernanceRequest":
        resolved_inputs = inputs or {}
        ctx = context or AutonomousGovernanceContext.from_inputs(
            supervision_id, subsystem_id, resolved_inputs,
        )
        all_domains = domains or list(SupervisionDomain)
        return cls(
            request_id        = request_id or str(uuid.uuid4()),
            supervision_id    = supervision_id,
            subsystem_id      = subsystem_id,
            workflow_type     = workflow_type,
            domains           = tuple(all_domains),
            context           = ctx,
            inputs            = resolved_inputs,
            metadata          = metadata or {},
        )

    def with_context(self, context: AutonomousGovernanceContext) -> "AutonomousGovernanceRequest":
        """Return a new request with the given context."""
        return AutonomousGovernanceRequest(
            request_id        = self.request_id,
            supervision_id    = self.supervision_id,
            subsystem_id      = self.subsystem_id,
            workflow_type     = self.workflow_type,
            domains           = self.domains,
            context           = context,
            inputs            = self.inputs,
            requested_at      = self.requested_at,
            metadata          = self.metadata,
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "supervision_id": self.supervision_id,
            "subsystem_id":   self.subsystem_id,
            "workflow_type":  self.workflow_type,
            "domains":        [d.value if hasattr(d, "value") else str(d) for d in self.domains],
            "context":        self.context.to_dict(),
            "requested_at":   self.requested_at,
            "framework_version": self.framework_version,
        }
