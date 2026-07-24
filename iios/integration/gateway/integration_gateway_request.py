"""
integration_gateway_request.py — iios.integration.gateway
-----------------------------------------------------------
IntegrationGatewayRequest — immutable request submitted to the gateway.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import GatewayOperationType, REQUEST_ID_PREFIX


@dataclass(frozen=True)
class IntegrationGatewayRequest:
    """
    Immutable descriptor for an operation submitted to the Enterprise
    Integration Gateway.

    All public API interactions (submit, connect, disconnect, validate,
    query) pass through this object.
    """

    request_id:       str
    operation:        GatewayOperationType
    workflow_id:      str
    enterprise_id:    str
    session_id:       str                   # optional; empty = new session
    payload:          Dict[str, Any]
    metadata:         Dict[str, str]
    connector_config: Dict[str, Any]
    protocol_config:  Dict[str, Any]
    auth_config:      Dict[str, Any]
    endpoint_config:  Dict[str, Any]
    platform_context: Dict[str, Any]
    submitted_at:     str

    # ─── factory ──────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        operation:        GatewayOperationType,
        workflow_id:      str,
        enterprise_id:    str,
        *,
        session_id:       str                        = "",
        payload:          Optional[Dict[str, Any]]   = None,
        metadata:         Optional[Dict[str, str]]   = None,
        connector_config: Optional[Dict[str, Any]]   = None,
        protocol_config:  Optional[Dict[str, Any]]   = None,
        auth_config:      Optional[Dict[str, Any]]   = None,
        endpoint_config:  Optional[Dict[str, Any]]   = None,
        platform_context: Optional[Dict[str, Any]]   = None,
        request_id:       Optional[str]              = None,
    ) -> "IntegrationGatewayRequest":
        return cls(
            request_id       = request_id or f"{REQUEST_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            operation        = operation,
            workflow_id      = workflow_id,
            enterprise_id    = enterprise_id,
            session_id       = session_id,
            payload          = dict(payload          or {}),
            metadata         = dict(metadata          or {}),
            connector_config = dict(connector_config or {}),
            protocol_config  = dict(protocol_config  or {}),
            auth_config      = dict(auth_config      or {}),
            endpoint_config  = dict(endpoint_config  or {}),
            platform_context = dict(platform_context or {}),
            submitted_at     = datetime.now(timezone.utc).isoformat(),
        )

    # ─── serialization ────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":       self.request_id,
            "operation":        self.operation.value,
            "workflow_id":      self.workflow_id,
            "enterprise_id":    self.enterprise_id,
            "session_id":       self.session_id,
            "payload":          dict(self.payload),
            "metadata":         dict(self.metadata),
            "connector_config": dict(self.connector_config),
            "protocol_config":  dict(self.protocol_config),
            "auth_config":      dict(self.auth_config),
            "endpoint_config":  dict(self.endpoint_config),
            "platform_context": dict(self.platform_context),
            "submitted_at":     self.submitted_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IntegrationGatewayRequest":
        return cls(
            request_id       = str(d["request_id"]),
            operation        = GatewayOperationType(d["operation"]),
            workflow_id      = str(d.get("workflow_id", "")),
            enterprise_id    = str(d.get("enterprise_id", "")),
            session_id       = str(d.get("session_id", "")),
            payload          = dict(d.get("payload", {})),
            metadata         = dict(d.get("metadata", {})),
            connector_config = dict(d.get("connector_config", {})),
            protocol_config  = dict(d.get("protocol_config", {})),
            auth_config      = dict(d.get("auth_config", {})),
            endpoint_config  = dict(d.get("endpoint_config", {})),
            platform_context = dict(d.get("platform_context", {})),
            submitted_at     = str(d.get("submitted_at", "")),
        )

    # ─── convenience properties ────────────────────────────────────────

    @property
    def is_submit(self) -> bool:
        return self.operation == GatewayOperationType.SUBMIT

    @property
    def is_query(self) -> bool:
        return self.operation == GatewayOperationType.QUERY

    @property
    def is_connect(self) -> bool:
        return self.operation == GatewayOperationType.CONNECT

    @property
    def is_disconnect(self) -> bool:
        return self.operation == GatewayOperationType.DISCONNECT

    @property
    def has_session(self) -> bool:
        return bool(self.session_id)

    def __repr__(self) -> str:
        return (
            f"IntegrationGatewayRequest("
            f"request_id={self.request_id!r}, "
            f"operation={self.operation.value!r}, "
            f"workflow_id={self.workflow_id!r})"
        )
