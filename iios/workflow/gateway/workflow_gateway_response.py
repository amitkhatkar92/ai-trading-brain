"""
workflow_gateway_response.py — iios.workflow.gateway
------------------------------------------------------
WorkflowGatewayResponse — immutable enterprise workflow gateway response.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import PREFIX_RESPONSE, GatewayResponseStatus
from .workflow_gateway_request import WorkflowGatewayRequest


@dataclass(frozen=True)
class WorkflowGatewayResponse:
    """
    Immutable gateway response — the only valid output of the Enterprise
    Workflow Gateway's public API.

    The gateway ALWAYS returns a response — never raises for
    workflow-level failures.  Error details are in ``error_message``
    and ``status == GatewayResponseStatus.FAILURE``.
    """
    response_id:         str
    request_id:          str
    workflow_id:         str
    session_id:          str
    status:              GatewayResponseStatus
    snapshot_id:         str
    data:                Dict[str, Any]
    error_message:       str
    warnings:            tuple                  # Tuple[str, ...]
    metadata:            Dict[str, Any]
    gateway_latency_ms:  float
    processing_time_ms:  float
    created_at:          str

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_success(self) -> bool:
        return self.status == GatewayResponseStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status == GatewayResponseStatus.FAILURE

    @property
    def is_pending(self) -> bool:
        return self.status == GatewayResponseStatus.PENDING

    @property
    def is_rejected(self) -> bool:
        return self.status == GatewayResponseStatus.REJECTED

    # ── Factories ─────────────────────────────────────────────────────────────

    @classmethod
    def success_for(
        cls,
        request:            WorkflowGatewayRequest,
        *,
        session_id:         str                    = "",
        snapshot_id:        str                    = "",
        data:               Optional[Dict[str, Any]] = None,
        warnings:           Optional[List[str]]    = None,
        metadata:           Optional[Dict[str, Any]] = None,
        gateway_latency_ms: float                  = 0.0,
        processing_time_ms: float                  = 0.0,
    ) -> "WorkflowGatewayResponse":
        return cls(
            response_id        = f"{PREFIX_RESPONSE}{uuid.uuid4().hex[:12]}",
            request_id         = request.request_id,
            workflow_id        = request.workflow_id,
            session_id         = session_id,
            status             = GatewayResponseStatus.SUCCESS,
            snapshot_id        = snapshot_id,
            data               = dict(data or {}),
            error_message      = "",
            warnings           = tuple(warnings or []),
            metadata           = dict(metadata or {}),
            gateway_latency_ms = round(gateway_latency_ms, 3),
            processing_time_ms = round(processing_time_ms, 3),
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def failure_for(
        cls,
        request:            WorkflowGatewayRequest,
        error_message:      str,
        *,
        session_id:         str                    = "",
        snapshot_id:        str                    = "",
        data:               Optional[Dict[str, Any]] = None,
        warnings:           Optional[List[str]]    = None,
        metadata:           Optional[Dict[str, Any]] = None,
        gateway_latency_ms: float                  = 0.0,
        processing_time_ms: float                  = 0.0,
    ) -> "WorkflowGatewayResponse":
        return cls(
            response_id        = f"{PREFIX_RESPONSE}{uuid.uuid4().hex[:12]}",
            request_id         = request.request_id,
            workflow_id        = request.workflow_id,
            session_id         = session_id,
            status             = GatewayResponseStatus.FAILURE,
            snapshot_id        = snapshot_id,
            data               = dict(data or {}),
            error_message      = error_message,
            warnings           = tuple(warnings or []),
            metadata           = dict(metadata or {}),
            gateway_latency_ms = round(gateway_latency_ms, 3),
            processing_time_ms = round(processing_time_ms, 3),
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def pending_for(
        cls,
        request:            WorkflowGatewayRequest,
        *,
        session_id:         str                    = "",
        metadata:           Optional[Dict[str, Any]] = None,
        gateway_latency_ms: float                  = 0.0,
    ) -> "WorkflowGatewayResponse":
        return cls(
            response_id        = f"{PREFIX_RESPONSE}{uuid.uuid4().hex[:12]}",
            request_id         = request.request_id,
            workflow_id        = request.workflow_id,
            session_id         = session_id,
            status             = GatewayResponseStatus.PENDING,
            snapshot_id        = "",
            data               = {},
            error_message      = "",
            warnings           = (),
            metadata           = dict(metadata or {}),
            gateway_latency_ms = round(gateway_latency_ms, 3),
            processing_time_ms = 0.0,
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def rejected_for(
        cls,
        request:            WorkflowGatewayRequest,
        reason:             str,
        *,
        gateway_latency_ms: float                  = 0.0,
    ) -> "WorkflowGatewayResponse":
        return cls(
            response_id        = f"{PREFIX_RESPONSE}{uuid.uuid4().hex[:12]}",
            request_id         = request.request_id,
            workflow_id        = request.workflow_id,
            session_id         = "",
            status             = GatewayResponseStatus.REJECTED,
            snapshot_id        = "",
            data               = {},
            error_message      = reason,
            warnings           = (),
            metadata           = {},
            gateway_latency_ms = round(gateway_latency_ms, 3),
            processing_time_ms = 0.0,
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":        self.response_id,
            "request_id":         self.request_id,
            "workflow_id":        self.workflow_id,
            "session_id":         self.session_id,
            "status":             self.status.value,
            "snapshot_id":        self.snapshot_id,
            "error_message":      self.error_message,
            "warnings":           list(self.warnings),
            "metadata":           dict(self.metadata),
            "gateway_latency_ms": self.gateway_latency_ms,
            "processing_time_ms": self.processing_time_ms,
            "created_at":         self.created_at,
            "is_success":         self.is_success,
            "is_failure":         self.is_failure,
            "is_pending":         self.is_pending,
            "is_rejected":        self.is_rejected,
        }
