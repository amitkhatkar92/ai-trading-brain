"""
workflow_request.py — iios.workflow.engine
-------------------------------------------
WorkflowEngineRequest — immutable descriptor for an enterprise
workflow execution request.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.workflow.lifecycle import WorkflowPriority, WorkflowType

from .constants import (
    DEFAULT_ENVIRONMENT,
    DEFAULT_PRIORITY,
    WorkflowDispatchMode,
    WorkflowQueuePriority,
)


@dataclass(frozen=True)
class WorkflowEngineRequest:
    """
    Immutable descriptor for an enterprise workflow execution request.

    Carries all information needed for the engine to coordinate
    a single workflow lifecycle from receipt through publication.
    """
    request_id:       str
    workflow_id:      str
    workflow_type:    WorkflowType
    dispatch_mode:    WorkflowDispatchMode
    priority:         int
    enterprise_id:    str
    correlation_id:   str
    trace_id:         str
    environment:      str
    payload:          Dict[str, Any]
    configuration:    Dict[str, Any]
    platform_context: Dict[str, Any]
    session_config:   Dict[str, Any]
    metadata:         Dict[str, Any]
    created_at:       str

    @classmethod
    def create(
        cls,
        workflow_id:   str,
        workflow_type: WorkflowType         = WorkflowType.SEQUENTIAL,
        dispatch_mode: WorkflowDispatchMode = WorkflowDispatchMode.IMMEDIATE,
        *,
        priority:         int                        = DEFAULT_PRIORITY,
        enterprise_id:    str                        = "iios",
        correlation_id:   str                        = "",
        trace_id:         str                        = "",
        environment:      str                        = DEFAULT_ENVIRONMENT,
        payload:          Optional[Dict[str, Any]]   = None,
        configuration:    Optional[Dict[str, Any]]   = None,
        platform_context: Optional[Dict[str, Any]]   = None,
        session_config:   Optional[Dict[str, Any]]   = None,
        metadata:         Optional[Dict[str, Any]]   = None,
        request_id:       Optional[str]              = None,
    ) -> "WorkflowEngineRequest":
        rid = request_id or f"wenreq-{uuid.uuid4().hex[:12]}"
        return cls(
            request_id       = rid,
            workflow_id      = workflow_id,
            workflow_type    = workflow_type,
            dispatch_mode    = dispatch_mode,
            priority         = max(0, min(3, priority)),   # clamp to 0-3
            enterprise_id    = enterprise_id,
            correlation_id   = correlation_id or f"cid-{uuid.uuid4().hex[:8]}",
            trace_id         = trace_id or f"tid-{uuid.uuid4().hex[:8]}",
            environment      = environment,
            payload          = dict(payload or {}),
            configuration    = dict(configuration or {}),
            platform_context = dict(platform_context or {}),
            session_config   = dict(session_config or {}),
            metadata         = dict(metadata or {}),
            created_at       = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ----------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------

    @property
    def is_immediate(self) -> bool:
        return self.dispatch_mode == WorkflowDispatchMode.IMMEDIATE

    @property
    def is_scheduled(self) -> bool:
        return self.dispatch_mode == WorkflowDispatchMode.SCHEDULED

    @property
    def is_event_driven(self) -> bool:
        return self.dispatch_mode == WorkflowDispatchMode.EVENT_DRIVEN

    @property
    def is_batch(self) -> bool:
        return self.dispatch_mode == WorkflowDispatchMode.BATCH

    @property
    def is_retry(self) -> bool:
        return self.dispatch_mode == WorkflowDispatchMode.RETRY

    # ----------------------------------------------------------------
    # Serialization
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":       self.request_id,
            "workflow_id":      self.workflow_id,
            "workflow_type":    self.workflow_type.value,
            "dispatch_mode":    self.dispatch_mode.value,
            "priority":         self.priority,
            "enterprise_id":    self.enterprise_id,
            "correlation_id":   self.correlation_id,
            "trace_id":         self.trace_id,
            "environment":      self.environment,
            "payload":          self.payload,
            "configuration":    self.configuration,
            "platform_context": self.platform_context,
            "session_config":   self.session_config,
            "metadata":         self.metadata,
            "created_at":       self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowEngineRequest":
        return cls(
            request_id       = d["request_id"],
            workflow_id      = d["workflow_id"],
            workflow_type    = WorkflowType(
                d.get("workflow_type", WorkflowType.SEQUENTIAL.value)
            ),
            dispatch_mode    = WorkflowDispatchMode(
                d.get("dispatch_mode", WorkflowDispatchMode.IMMEDIATE.value)
            ),
            priority         = d.get("priority", DEFAULT_PRIORITY),
            enterprise_id    = d.get("enterprise_id", "iios"),
            correlation_id   = d.get("correlation_id", ""),
            trace_id         = d.get("trace_id", ""),
            environment      = d.get("environment", DEFAULT_ENVIRONMENT),
            payload          = d.get("payload", {}),
            configuration    = d.get("configuration", {}),
            platform_context = d.get("platform_context", {}),
            session_config   = d.get("session_config", {}),
            metadata         = d.get("metadata", {}),
            created_at       = d["created_at"],
        )
