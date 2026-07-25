"""
workflow_gateway_context.py — iios.workflow.gateway
-----------------------------------------------------
WorkflowGatewayContext — execution context for a single gateway request.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import PREFIX_CONTEXT
from .workflow_gateway_request import WorkflowGatewayRequest


@dataclass(frozen=True)
class WorkflowGatewayContext:
    """
    Immutable execution context for a single gateway request.

    Carries gateway-level metadata, component context snapshots,
    and routing decisions for a single request lifecycle.
    """
    context_id:         str
    gateway_id:         str
    request_id:         str
    workflow_id:        str
    correlation_id:     str
    trace_id:           str
    environment:        str
    component_context:  Dict[str, Any]
    routing_context:    Dict[str, Any]
    metadata:           Dict[str, Any]
    created_at:         str

    @classmethod
    def create(
        cls,
        request:    WorkflowGatewayRequest,
        gateway_id: str,
        *,
        component_context: Optional[Dict[str, Any]] = None,
        routing_context:   Optional[Dict[str, Any]] = None,
        metadata:          Optional[Dict[str, Any]] = None,
        context_id:        Optional[str]            = None,
    ) -> "WorkflowGatewayContext":
        return cls(
            context_id        = context_id or f"{PREFIX_CONTEXT}{uuid.uuid4().hex[:12]}",
            gateway_id        = gateway_id,
            request_id        = request.request_id,
            workflow_id       = request.workflow_id,
            correlation_id    = request.correlation_id,
            trace_id          = request.trace_id,
            environment       = request.environment,
            component_context = dict(component_context or {}),
            routing_context   = dict(routing_context or {}),
            metadata          = dict(metadata or {}),
            created_at        = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "gateway_id":        self.gateway_id,
            "request_id":        self.request_id,
            "workflow_id":       self.workflow_id,
            "correlation_id":    self.correlation_id,
            "trace_id":          self.trace_id,
            "environment":       self.environment,
            "metadata":          dict(self.metadata),
            "created_at":        self.created_at,
        }
