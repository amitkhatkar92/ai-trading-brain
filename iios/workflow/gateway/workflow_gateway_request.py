"""
workflow_gateway_request.py — iios.workflow.gateway
-----------------------------------------------------
WorkflowGatewayRequest — immutable enterprise workflow gateway request.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_ENTERPRISE_ID,
    DEFAULT_ENVIRONMENT,
    DEFAULT_PRIORITY,
    PREFIX_REQUEST,
    GatewayRequestType,
)


@dataclass(frozen=True)
class WorkflowGatewayRequest:
    """
    Immutable gateway request — the only valid input to the Enterprise
    Workflow Gateway's public API.

    Carries all information needed to coordinate a full workflow
    submission, query, cancellation, or retry.
    """
    request_id:        str
    request_type:      GatewayRequestType
    workflow_id:       str
    workflow_name:     str
    enterprise_id:     str
    correlation_id:    str
    trace_id:          str
    environment:       str
    priority:          int
    payload:           Dict[str, Any]
    configuration:     Dict[str, Any]
    platform_context:  Dict[str, Any]
    enterprise_context: Dict[str, Any]
    metadata:          Dict[str, Any]
    tags:              Dict[str, str]
    created_at:        str

    @classmethod
    def create(
        cls,
        workflow_id:    str,
        workflow_name:  str                        = "",
        *,
        request_type:      GatewayRequestType     = GatewayRequestType.SUBMIT,
        enterprise_id:     str                    = DEFAULT_ENTERPRISE_ID,
        correlation_id:    str                    = "",
        trace_id:          str                    = "",
        environment:       str                    = DEFAULT_ENVIRONMENT,
        priority:          int                    = DEFAULT_PRIORITY,
        payload:           Optional[Dict[str, Any]] = None,
        configuration:     Optional[Dict[str, Any]] = None,
        platform_context:  Optional[Dict[str, Any]] = None,
        enterprise_context: Optional[Dict[str, Any]] = None,
        metadata:          Optional[Dict[str, Any]] = None,
        tags:              Optional[Dict[str, str]]  = None,
        request_id:        Optional[str]           = None,
    ) -> "WorkflowGatewayRequest":
        return cls(
            request_id         = request_id or f"{PREFIX_REQUEST}{uuid.uuid4().hex[:12]}",
            request_type       = request_type,
            workflow_id        = workflow_id,
            workflow_name      = workflow_name or workflow_id,
            enterprise_id      = enterprise_id,
            correlation_id     = correlation_id or f"cid-{uuid.uuid4().hex[:8]}",
            trace_id           = trace_id or f"tid-{uuid.uuid4().hex[:8]}",
            environment        = environment,
            priority           = max(0, min(10, priority)),
            payload            = dict(payload or {}),
            configuration      = dict(configuration or {}),
            platform_context   = dict(platform_context or {}),
            enterprise_context = dict(enterprise_context or {}),
            metadata           = dict(metadata or {}),
            tags               = dict(tags or {}),
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":         self.request_id,
            "request_type":       self.request_type.value,
            "workflow_id":        self.workflow_id,
            "workflow_name":      self.workflow_name,
            "enterprise_id":      self.enterprise_id,
            "correlation_id":     self.correlation_id,
            "trace_id":           self.trace_id,
            "environment":        self.environment,
            "priority":           self.priority,
            "metadata":           dict(self.metadata),
            "tags":               dict(self.tags),
            "created_at":         self.created_at,
        }
