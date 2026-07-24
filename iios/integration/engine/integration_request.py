"""
integration_request.py — iios.integration.engine
--------------------------------------------------
IntegrationRequest — immutable request data object.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import (
    AdapterType,
    ConnectorType,
    DEFAULT_ENVIRONMENT,
    DEFAULT_PRIORITY,
    DispatchMode,
    ProtocolType,
)


@dataclass(frozen=True)
class IntegrationRequest:
    """
    Immutable descriptor for an enterprise integration request.

    Carries all information needed for the engine to coordinate
    a single integration workflow.
    """
    request_id:      str
    connector_type:  ConnectorType
    adapter_type:    AdapterType
    protocol_type:   ProtocolType
    dispatch_mode:   DispatchMode
    endpoint:        str
    payload:         Dict[str, Any]
    headers:         Dict[str, str]
    auth_config:     Dict[str, Any]
    metadata:        Dict[str, Any]
    correlation_id:  str
    trace_id:        str
    priority:        int
    environment:     str
    created_at:      str

    @classmethod
    def create(
        cls,
        connector_type:  ConnectorType,
        adapter_type:    AdapterType    = AdapterType.GENERIC,
        protocol_type:   ProtocolType   = ProtocolType.INTERNAL,
        dispatch_mode:   DispatchMode   = DispatchMode.IMMEDIATE,
        *,
        endpoint:       str                        = "",
        payload:        Optional[Dict[str, Any]]   = None,
        headers:        Optional[Dict[str, str]]   = None,
        auth_config:    Optional[Dict[str, Any]]   = None,
        metadata:       Optional[Dict[str, Any]]   = None,
        correlation_id: str                        = "",
        trace_id:       str                        = "",
        priority:       int                        = DEFAULT_PRIORITY,
        environment:    str                        = DEFAULT_ENVIRONMENT,
        request_id:     Optional[str]              = None,
    ) -> "IntegrationRequest":
        rid = request_id or f"req-{uuid.uuid4().hex[:16]}"
        return cls(
            request_id     = rid,
            connector_type = connector_type,
            adapter_type   = adapter_type,
            protocol_type  = protocol_type,
            dispatch_mode  = dispatch_mode,
            endpoint       = endpoint,
            payload        = dict(payload or {}),
            headers        = dict(headers or {}),
            auth_config    = dict(auth_config or {}),
            metadata       = dict(metadata or {}),
            correlation_id = correlation_id or f"cid-{uuid.uuid4().hex[:8]}",
            trace_id       = trace_id or f"tid-{uuid.uuid4().hex[:8]}",
            priority       = priority,
            environment    = environment,
            created_at     = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "connector_type": self.connector_type.value,
            "adapter_type":   self.adapter_type.value,
            "protocol_type":  self.protocol_type.value,
            "dispatch_mode":  self.dispatch_mode.value,
            "endpoint":       self.endpoint,
            "payload":        self.payload,
            "headers":        self.headers,
            "auth_config":    self.auth_config,
            "metadata":       self.metadata,
            "correlation_id": self.correlation_id,
            "trace_id":       self.trace_id,
            "priority":       self.priority,
            "environment":    self.environment,
            "created_at":     self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IntegrationRequest":
        return cls(
            request_id     = d["request_id"],
            connector_type = ConnectorType(d["connector_type"]),
            adapter_type   = AdapterType(d.get("adapter_type", AdapterType.GENERIC.value)),
            protocol_type  = ProtocolType(d.get("protocol_type", ProtocolType.INTERNAL.value)),
            dispatch_mode  = DispatchMode(d.get("dispatch_mode", DispatchMode.IMMEDIATE.value)),
            endpoint       = d.get("endpoint", ""),
            payload        = d.get("payload", {}),
            headers        = d.get("headers", {}),
            auth_config    = d.get("auth_config", {}),
            metadata       = d.get("metadata", {}),
            correlation_id = d.get("correlation_id", ""),
            trace_id       = d.get("trace_id", ""),
            priority       = d.get("priority", DEFAULT_PRIORITY),
            environment    = d.get("environment", DEFAULT_ENVIRONMENT),
            created_at     = d["created_at"],
        )
