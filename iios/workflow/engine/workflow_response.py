"""
workflow_response.py — iios.workflow.engine
--------------------------------------------
WorkflowEngineResponse — immutable result of a workflow engine execution.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import WorkflowEngineResponseStatus
from .workflow_request import WorkflowEngineRequest


@dataclass(frozen=True)
class WorkflowEngineResponse:
    """
    Immutable result of a workflow engine execution.

    The engine always returns a WorkflowEngineResponse — never raises
    for workflow-level errors.  Error details are in ``error_message``
    and ``status == "failure"``.
    """
    response_id:      str
    request_id:       str
    session_id:       str
    status:           WorkflowEngineResponseStatus
    data:             Dict[str, Any]
    snapshot_id:      str
    error_message:    str
    metadata:         Dict[str, Any]
    latency_ms:       float
    queue_time_ms:    float
    processing_time_ms: float
    created_at:       str

    # ----------------------------------------------------------------
    # Factories
    # ----------------------------------------------------------------

    @classmethod
    def success_for(
        cls,
        request:            WorkflowEngineRequest,
        session_id:         str,
        *,
        data:               Optional[Dict[str, Any]] = None,
        snapshot_id:        str   = "",
        latency_ms:         float = 0.0,
        queue_time_ms:      float = 0.0,
        processing_time_ms: float = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowEngineResponse":
        return cls(
            response_id        = f"wenresp-{uuid.uuid4().hex[:12]}",
            request_id         = request.request_id,
            session_id         = session_id,
            status             = WorkflowEngineResponseStatus.SUCCESS,
            data               = dict(data or {}),
            snapshot_id        = snapshot_id,
            error_message      = "",
            metadata           = dict(metadata or {}),
            latency_ms         = round(latency_ms, 3),
            queue_time_ms      = round(queue_time_ms, 3),
            processing_time_ms = round(processing_time_ms, 3),
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def failure_for(
        cls,
        request:            WorkflowEngineRequest,
        session_id:         str,
        error_message:      str,
        *,
        latency_ms:         float = 0.0,
        queue_time_ms:      float = 0.0,
        processing_time_ms: float = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowEngineResponse":
        return cls(
            response_id        = f"wenresp-{uuid.uuid4().hex[:12]}",
            request_id         = request.request_id,
            session_id         = session_id,
            status             = WorkflowEngineResponseStatus.FAILURE,
            data               = {},
            snapshot_id        = "",
            error_message      = error_message,
            metadata           = dict(metadata or {}),
            latency_ms         = round(latency_ms, 3),
            queue_time_ms      = round(queue_time_ms, 3),
            processing_time_ms = round(processing_time_ms, 3),
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def cancelled_for(
        cls,
        request:   WorkflowEngineRequest,
        session_id: str,
        *,
        latency_ms: float = 0.0,
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> "WorkflowEngineResponse":
        return cls(
            response_id        = f"wenresp-{uuid.uuid4().hex[:12]}",
            request_id         = request.request_id,
            session_id         = session_id,
            status             = WorkflowEngineResponseStatus.CANCELLED,
            data               = {},
            snapshot_id        = "",
            error_message      = "workflow cancelled",
            metadata           = dict(metadata or {}),
            latency_ms         = round(latency_ms, 3),
            queue_time_ms      = 0.0,
            processing_time_ms = 0.0,
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ----------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------

    @property
    def is_success(self) -> bool:
        return self.status == WorkflowEngineResponseStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status == WorkflowEngineResponseStatus.FAILURE

    @property
    def is_cancelled(self) -> bool:
        return self.status == WorkflowEngineResponseStatus.CANCELLED

    @property
    def has_snapshot(self) -> bool:
        return bool(self.snapshot_id)

    # ----------------------------------------------------------------
    # Serialization
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":       self.response_id,
            "request_id":        self.request_id,
            "session_id":        self.session_id,
            "status":            self.status.value,
            "data":              self.data,
            "snapshot_id":       self.snapshot_id,
            "error_message":     self.error_message,
            "metadata":          self.metadata,
            "latency_ms":        self.latency_ms,
            "queue_time_ms":     self.queue_time_ms,
            "processing_time_ms": self.processing_time_ms,
            "created_at":        self.created_at,
            "is_success":        self.is_success,
            "is_failure":        self.is_failure,
            "is_cancelled":      self.is_cancelled,
        }
