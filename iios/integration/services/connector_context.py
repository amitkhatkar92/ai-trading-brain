"""
connector_context.py — iios.integration.services
--------------------------------------------------
ConnectorContext — execution context for a single connector invocation.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import AuthScheme, ConnectorStatus, ServiceType, TransportType


@dataclass(frozen=True)
class ConnectorContext:
    """
    Immutable execution context for one connector invocation.

    Carries all runtime information needed to execute a connector:
    service type, transport, auth scheme, endpoint, configuration,
    and metadata linking back to the approved integration request.
    """

    context_id:          str
    request_id:          str       # approved integration request ID
    session_id:          str
    service_type:        ServiceType
    transport_type:      TransportType
    auth_scheme:         AuthScheme
    endpoint:            str
    timeout_ms:          int
    retry_max_attempts:  int
    connector_config:    Dict[str, Any]
    auth_config:         Dict[str, Any]
    transport_config:    Dict[str, Any]
    metadata:            Dict[str, Any]
    status:              ConnectorStatus
    created_at:          str

    @classmethod
    def create(
        cls,
        request_id:          str,
        session_id:          str,
        service_type:        ServiceType,
        transport_type:      TransportType   = TransportType.HTTP,
        auth_scheme:         AuthScheme      = AuthScheme.NONE,
        endpoint:            str             = "",
        timeout_ms:          int             = 30_000,
        retry_max_attempts:  int             = 3,
        *,
        connector_config:    Optional[Dict[str, Any]] = None,
        auth_config:         Optional[Dict[str, Any]] = None,
        transport_config:    Optional[Dict[str, Any]] = None,
        metadata:            Optional[Dict[str, Any]] = None,
        context_id:          Optional[str]            = None,
    ) -> "ConnectorContext":
        return cls(
            context_id         = context_id or f"sctx-{uuid.uuid4().hex[:12]}",
            request_id         = request_id,
            session_id         = session_id,
            service_type       = service_type,
            transport_type     = transport_type,
            auth_scheme        = auth_scheme,
            endpoint           = endpoint,
            timeout_ms         = timeout_ms,
            retry_max_attempts = retry_max_attempts,
            connector_config   = dict(connector_config   or {}),
            auth_config        = dict(auth_config        or {}),
            transport_config   = dict(transport_config   or {}),
            metadata           = dict(metadata           or {}),
            status             = ConnectorStatus.IDLE,
            created_at         = datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":         self.context_id,
            "request_id":         self.request_id,
            "session_id":         self.session_id,
            "service_type":       self.service_type.value,
            "transport_type":     self.transport_type.value,
            "auth_scheme":        self.auth_scheme.value,
            "endpoint":           self.endpoint,
            "timeout_ms":         self.timeout_ms,
            "retry_max_attempts": self.retry_max_attempts,
            "connector_config":   self.connector_config,
            "auth_config":        self.auth_config,
            "transport_config":   self.transport_config,
            "metadata":           self.metadata,
            "status":             self.status.value,
            "created_at":         self.created_at,
        }
