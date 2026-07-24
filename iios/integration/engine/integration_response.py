"""
integration_response.py — iios.integration.engine
---------------------------------------------------
IntegrationResponse — immutable response data object.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import IntegrationResponseStatus
from .integration_request import IntegrationRequest


@dataclass(frozen=True)
class IntegrationResponse:
    """
    Immutable result of an integration workflow execution.

    The engine always returns an IntegrationResponse — never raises
    for integration-level errors.  Error details are captured in
    ``error_message`` and ``status == "failure"``.
    """
    response_id:   str
    request_id:    str
    session_id:    str
    status:        IntegrationResponseStatus
    data:          Dict[str, Any]
    error_message: str
    metadata:      Dict[str, Any]
    latency_ms:    float
    created_at:    str

    # ----------------------------------------------------------------
    # Factories
    # ----------------------------------------------------------------

    @classmethod
    def success_for(
        cls,
        request:    IntegrationRequest,
        session_id: str,
        data:       Optional[Dict[str, Any]] = None,
        latency_ms: float = 0.0,
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> "IntegrationResponse":
        return cls(
            response_id   = f"resp-{uuid.uuid4().hex[:16]}",
            request_id    = request.request_id,
            session_id    = session_id,
            status        = IntegrationResponseStatus.SUCCESS,
            data          = dict(data or {}),
            error_message = "",
            metadata      = dict(metadata or {}),
            latency_ms    = round(latency_ms, 3),
            created_at    = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def failure_for(
        cls,
        request:       IntegrationRequest,
        session_id:    str,
        error_message: str,
        latency_ms:    float = 0.0,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> "IntegrationResponse":
        return cls(
            response_id   = f"resp-{uuid.uuid4().hex[:16]}",
            request_id    = request.request_id,
            session_id    = session_id,
            status        = IntegrationResponseStatus.FAILURE,
            data          = {},
            error_message = error_message,
            metadata      = dict(metadata or {}),
            latency_ms    = round(latency_ms, 3),
            created_at    = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    @property
    def is_success(self) -> bool:
        return self.status == IntegrationResponseStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status == IntegrationResponseStatus.FAILURE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":   self.response_id,
            "request_id":    self.request_id,
            "session_id":    self.session_id,
            "status":        self.status.value,
            "data":          self.data,
            "error_message": self.error_message,
            "metadata":      self.metadata,
            "latency_ms":    self.latency_ms,
            "created_at":    self.created_at,
        }
