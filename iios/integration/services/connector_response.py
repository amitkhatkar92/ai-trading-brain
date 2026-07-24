"""
connector_response.py — iios.integration.services
---------------------------------------------------
ConnectorResponse — result returned by the services engine.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import ServiceResponseStatus


@dataclass(frozen=True)
class ConnectorResponse:
    """
    Immutable response returned after integration service execution.
    """

    response_id:     str
    request_id:      str
    status:          ServiceResponseStatus
    data:            Dict[str, Any]
    error_message:   str
    latency_ms:      float
    retry_count:     int
    connector_id:    str
    adapter_id:      str
    transport:       str
    metadata:        Dict[str, Any]
    created_at:      str

    @classmethod
    def success(
        cls,
        request_id:   str,
        data:         Optional[Dict[str, Any]] = None,
        latency_ms:   float                    = 0.0,
        retry_count:  int                      = 0,
        connector_id: str                      = "",
        adapter_id:   str                      = "",
        transport:    str                      = "",
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> "ConnectorResponse":
        return cls(
            response_id   = f"srsp-{uuid.uuid4().hex[:12]}",
            request_id    = request_id,
            status        = ServiceResponseStatus.SUCCESS,
            data          = dict(data     or {}),
            error_message = "",
            latency_ms    = latency_ms,
            retry_count   = retry_count,
            connector_id  = connector_id,
            adapter_id    = adapter_id,
            transport     = transport,
            metadata      = dict(metadata or {}),
            created_at    = datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def failure(
        cls,
        request_id:    str,
        error_message: str,
        status:        ServiceResponseStatus = ServiceResponseStatus.FAILURE,
        latency_ms:    float                 = 0.0,
        retry_count:   int                   = 0,
        connector_id:  str                   = "",
        adapter_id:    str                   = "",
        transport:     str                   = "",
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> "ConnectorResponse":
        return cls(
            response_id   = f"srsp-{uuid.uuid4().hex[:12]}",
            request_id    = request_id,
            status        = status,
            data          = {},
            error_message = error_message,
            latency_ms    = latency_ms,
            retry_count   = retry_count,
            connector_id  = connector_id,
            adapter_id    = adapter_id,
            transport     = transport,
            metadata      = dict(metadata or {}),
            created_at    = datetime.now(timezone.utc).isoformat(),
        )

    @property
    def is_success(self) -> bool:
        return self.status == ServiceResponseStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status != ServiceResponseStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":   self.response_id,
            "request_id":    self.request_id,
            "status":        self.status.value,
            "data":          self.data,
            "error_message": self.error_message,
            "latency_ms":    self.latency_ms,
            "retry_count":   self.retry_count,
            "connector_id":  self.connector_id,
            "adapter_id":    self.adapter_id,
            "transport":     self.transport,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }
