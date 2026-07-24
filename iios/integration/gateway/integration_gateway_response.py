"""
integration_gateway_response.py — iios.integration.gateway
------------------------------------------------------------
IntegrationGatewayResponse — immutable result returned by the gateway.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import (
    GatewayOperationType,
    GatewayResponseStatus,
    GatewayState,
    RESPONSE_ID_PREFIX,
)


@dataclass(frozen=True)
class IntegrationGatewayResponse:
    """
    Immutable response returned for every gateway operation.

    Carries the full coordination result: lifecycle session,
    engine result reference, governance decision, snapshot reference,
    and timing information.
    """

    response_id:            str
    request_id:             str
    status:                 GatewayResponseStatus
    gateway_state:          GatewayState
    operation:              GatewayOperationType
    lifecycle_session_id:   str
    engine_request_id:      str
    governance_decision:    str
    snapshot_id:            str
    data:                   Dict[str, Any]
    error:                  str
    error_code:             str
    processing_time_ms:     float
    completed_at:           str

    # ─── factories ────────────────────────────────────────────────────

    @classmethod
    def success(
        cls,
        request_id:           str,
        operation:            GatewayOperationType,
        gateway_state:        GatewayState,
        *,
        lifecycle_session_id: str                        = "",
        engine_request_id:    str                        = "",
        governance_decision:  str                        = "",
        snapshot_id:          str                        = "",
        data:                 Optional[Dict[str, Any]]   = None,
        processing_time_ms:   float                      = 0.0,
        response_id:          Optional[str]              = None,
    ) -> "IntegrationGatewayResponse":
        return cls(
            response_id          = response_id or f"{RESPONSE_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            request_id           = request_id,
            status               = GatewayResponseStatus.SUCCESS,
            gateway_state        = gateway_state,
            operation            = operation,
            lifecycle_session_id = lifecycle_session_id,
            engine_request_id    = engine_request_id,
            governance_decision  = governance_decision,
            snapshot_id          = snapshot_id,
            data                 = dict(data or {}),
            error                = "",
            error_code           = "",
            processing_time_ms   = processing_time_ms,
            completed_at         = datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def failure(
        cls,
        request_id:           str,
        operation:            GatewayOperationType,
        gateway_state:        GatewayState,
        error:                str,
        *,
        error_code:           str                        = "",
        lifecycle_session_id: str                        = "",
        engine_request_id:    str                        = "",
        governance_decision:  str                        = "",
        snapshot_id:          str                        = "",
        data:                 Optional[Dict[str, Any]]   = None,
        processing_time_ms:   float                      = 0.0,
        response_id:          Optional[str]              = None,
    ) -> "IntegrationGatewayResponse":
        return cls(
            response_id          = response_id or f"{RESPONSE_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            request_id           = request_id,
            status               = GatewayResponseStatus.FAILED,
            gateway_state        = gateway_state,
            operation            = operation,
            lifecycle_session_id = lifecycle_session_id,
            engine_request_id    = engine_request_id,
            governance_decision  = governance_decision,
            snapshot_id          = snapshot_id,
            data                 = dict(data or {}),
            error                = error,
            error_code           = error_code,
            processing_time_ms   = processing_time_ms,
            completed_at         = datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def partial(
        cls,
        request_id:           str,
        operation:            GatewayOperationType,
        gateway_state:        GatewayState,
        *,
        lifecycle_session_id: str                        = "",
        engine_request_id:    str                        = "",
        governance_decision:  str                        = "",
        snapshot_id:          str                        = "",
        data:                 Optional[Dict[str, Any]]   = None,
        error:                str                        = "",
        processing_time_ms:   float                      = 0.0,
        response_id:          Optional[str]              = None,
    ) -> "IntegrationGatewayResponse":
        return cls(
            response_id          = response_id or f"{RESPONSE_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            request_id           = request_id,
            status               = GatewayResponseStatus.PARTIAL,
            gateway_state        = gateway_state,
            operation            = operation,
            lifecycle_session_id = lifecycle_session_id,
            engine_request_id    = engine_request_id,
            governance_decision  = governance_decision,
            snapshot_id          = snapshot_id,
            data                 = dict(data or {}),
            error                = error,
            error_code           = "",
            processing_time_ms   = processing_time_ms,
            completed_at         = datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def rejected(
        cls,
        request_id:           str,
        operation:            GatewayOperationType,
        gateway_state:        GatewayState,
        reason:               str,
        *,
        error_code:           str                        = "",
        processing_time_ms:   float                      = 0.0,
        response_id:          Optional[str]              = None,
    ) -> "IntegrationGatewayResponse":
        return cls(
            response_id          = response_id or f"{RESPONSE_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            request_id           = request_id,
            status               = GatewayResponseStatus.REJECTED,
            gateway_state        = gateway_state,
            operation            = operation,
            lifecycle_session_id = "",
            engine_request_id    = "",
            governance_decision  = "rejected",
            snapshot_id          = "",
            data                 = {},
            error                = reason,
            error_code           = error_code,
            processing_time_ms   = processing_time_ms,
            completed_at         = datetime.now(timezone.utc).isoformat(),
        )

    # ─── convenience properties ────────────────────────────────────────

    @property
    def is_successful(self) -> bool:
        return self.status == GatewayResponseStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status in (
            GatewayResponseStatus.FAILED,
            GatewayResponseStatus.REJECTED,
        )

    @property
    def has_snapshot(self) -> bool:
        return bool(self.snapshot_id)

    @property
    def has_lifecycle_session(self) -> bool:
        return bool(self.lifecycle_session_id)

    # ─── serialization ────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":          self.response_id,
            "request_id":           self.request_id,
            "status":               self.status.value,
            "gateway_state":        self.gateway_state.value,
            "operation":            self.operation.value,
            "lifecycle_session_id": self.lifecycle_session_id,
            "engine_request_id":    self.engine_request_id,
            "governance_decision":  self.governance_decision,
            "snapshot_id":          self.snapshot_id,
            "data":                 dict(self.data),
            "error":                self.error,
            "error_code":           self.error_code,
            "processing_time_ms":   self.processing_time_ms,
            "completed_at":         self.completed_at,
        }

    def __repr__(self) -> str:
        return (
            f"IntegrationGatewayResponse("
            f"response_id={self.response_id!r}, "
            f"status={self.status.value!r}, "
            f"request_id={self.request_id!r})"
        )
