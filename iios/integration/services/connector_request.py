"""
connector_request.py — iios.integration.services
--------------------------------------------------
ConnectorRequest — approved request submitted to the services engine.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import AuthScheme, RetryStrategy, ServiceType, TransportType


@dataclass(frozen=True)
class ConnectorRequest:
    """
    Immutable approved request submitted to the Integration Services Engine.

    Carries the governance-approved integration specification.
    The engine uses this to load connectors, adapters, and protocols
    and execute the integration workflow.
    """

    request_id:          str
    approved_request_id: str        # from M2 IntegrationRequest
    service_type:        ServiceType
    transport_type:      TransportType
    auth_scheme:         AuthScheme
    retry_strategy:      RetryStrategy
    endpoint:            str
    payload:             Dict[str, Any]
    headers:             Dict[str, str]
    auth_config:         Dict[str, Any]
    connector_config:    Dict[str, Any]
    transport_config:    Dict[str, Any]
    metadata:            Dict[str, Any]
    correlation_id:      str
    trace_id:            str
    timeout_ms:          int
    retry_max_attempts:  int
    created_at:          str

    @classmethod
    def create(
        cls,
        approved_request_id: str,
        service_type:        ServiceType,
        transport_type:      TransportType  = TransportType.HTTP,
        auth_scheme:         AuthScheme     = AuthScheme.NONE,
        retry_strategy:      RetryStrategy  = RetryStrategy.EXPONENTIAL_BACKOFF,
        endpoint:            str            = "",
        *,
        payload:             Optional[Dict[str, Any]] = None,
        headers:             Optional[Dict[str, str]] = None,
        auth_config:         Optional[Dict[str, Any]] = None,
        connector_config:    Optional[Dict[str, Any]] = None,
        transport_config:    Optional[Dict[str, Any]] = None,
        metadata:            Optional[Dict[str, Any]] = None,
        correlation_id:      str                      = "",
        trace_id:            str                      = "",
        timeout_ms:          int                      = 30_000,
        retry_max_attempts:  int                      = 3,
        request_id:          Optional[str]            = None,
    ) -> "ConnectorRequest":
        return cls(
            request_id          = request_id or f"sreq-{uuid.uuid4().hex[:12]}",
            approved_request_id = approved_request_id,
            service_type        = service_type,
            transport_type      = transport_type,
            auth_scheme         = auth_scheme,
            retry_strategy      = retry_strategy,
            endpoint            = endpoint,
            payload             = dict(payload          or {}),
            headers             = dict(headers          or {}),
            auth_config         = dict(auth_config      or {}),
            connector_config    = dict(connector_config or {}),
            transport_config    = dict(transport_config or {}),
            metadata            = dict(metadata         or {}),
            correlation_id      = correlation_id or f"corr-{uuid.uuid4().hex[:8]}",
            trace_id            = trace_id       or f"trc-{uuid.uuid4().hex[:8]}",
            timeout_ms          = timeout_ms,
            retry_max_attempts  = retry_max_attempts,
            created_at          = datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":          self.request_id,
            "approved_request_id": self.approved_request_id,
            "service_type":        self.service_type.value,
            "transport_type":      self.transport_type.value,
            "auth_scheme":         self.auth_scheme.value,
            "retry_strategy":      self.retry_strategy.value,
            "endpoint":            self.endpoint,
            "payload":             self.payload,
            "headers":             self.headers,
            "auth_config":         self.auth_config,
            "connector_config":    self.connector_config,
            "transport_config":    self.transport_config,
            "metadata":            self.metadata,
            "correlation_id":      self.correlation_id,
            "trace_id":            self.trace_id,
            "timeout_ms":          self.timeout_ms,
            "retry_max_attempts":  self.retry_max_attempts,
            "created_at":          self.created_at,
        }
