"""
supervisor_factory.py — iios.supervisor.engine
-----------------------------------------------
Central factory for all supervisor engine value objects.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    FACTORY_SYSTEM_ID,
    EngineState,
    ResponseStatus,
    SchedulerPriority,
    SupervisorWorkflowType,
)
from .supervisor_context import SupervisorEngineContext
from .supervisor_pipeline import SupervisorPipeline
from .supervisor_request import SupervisorRequest
from .supervisor_response import SupervisorResponse, SupervisorEngineSnapshot


class SupervisorEngineFactory:
    """
    Static-method factory for supervisor engine value objects.

    All methods are pure — they carry no state and have no side-effects.
    """

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    @staticmethod
    def create_context(
        supervision_id: str,
        subsystem_id:   str,
        workflow_type:  SupervisorWorkflowType,
        *,
        priority: SchedulerPriority             = SchedulerPriority.NORMAL,
        metadata: Optional[Dict[str, Any]]      = None,
    ) -> SupervisorEngineContext:
        return SupervisorEngineContext.create(
            supervision_id,
            subsystem_id,
            workflow_type,
            priority = priority,
            metadata = dict(metadata or {}),
        )

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    @staticmethod
    def create_request(
        supervision_id: str,
        subsystem_id:   str,
        workflow_type:  SupervisorWorkflowType = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        *,
        priority: SchedulerPriority             = SchedulerPriority.NORMAL,
        inputs:   Optional[Dict[str, Any]]      = None,
        metadata: Optional[Dict[str, Any]]      = None,
    ) -> SupervisorRequest:
        ctx = SupervisorEngineFactory.create_context(
            supervision_id, subsystem_id, workflow_type, priority=priority
        )
        return SupervisorRequest.create(
            supervision_id,
            subsystem_id,
            workflow_type,
            priority = priority,
            context  = ctx,
            inputs   = dict(inputs or {}),
            metadata = dict(metadata or {}),
        )

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def create_pipeline(request: SupervisorRequest) -> SupervisorPipeline:
        return SupervisorPipeline(
            request_id     = request.request_id,
            supervision_id = request.supervision_id,
            subsystem_id   = request.subsystem_id,
            workflow_type  = request.workflow_type,
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    @staticmethod
    def create_snapshot(
        pipeline:           SupervisorPipeline,
        engine_state:       EngineState,
        *,
        subsystems_collected: Optional[List[str]] = None,
        health_summary:       str                 = "",
        outputs:              Optional[Dict[str, Any]] = None,
    ) -> SupervisorEngineSnapshot:
        return SupervisorEngineSnapshot.create(
            supervision_id = pipeline.supervision_id,
            subsystem_id   = pipeline.subsystem_id,
            session_id     = pipeline.session_id,
            workflow_type  = pipeline.workflow_type,
            engine_state   = engine_state,
            subsystems_collected = list(subsystems_collected or []),
            health_summary = dict(health_summary) if isinstance(health_summary, dict) else {},
            outputs        = dict(outputs or {}),
        )

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------

    @staticmethod
    def create_success_response(
        request:  SupervisorRequest,
        pipeline: SupervisorPipeline,
        *,
        snapshot:  Optional[SupervisorEngineSnapshot] = None,
        metadata:  Optional[Dict[str, Any]]           = None,
    ) -> SupervisorResponse:
        elapsed = pipeline.elapsed_s
        return SupervisorResponse(
            response_id    = str(uuid.uuid4()),
            request_id     = request.request_id,
            supervision_id = request.supervision_id,
            subsystem_id   = request.subsystem_id,
            workflow_type  = request.workflow_type,
            status         = ResponseStatus.SUCCESS,
            snapshot       = snapshot,
            elapsed_s      = elapsed,
            metadata       = dict(metadata or {}),
        )

    @staticmethod
    def create_failure_response(
        request:       SupervisorRequest,
        pipeline:      Optional[SupervisorPipeline] = None,
        *,
        error_message: str                         = "",
        metadata:      Optional[Dict[str, Any]]    = None,
    ) -> SupervisorResponse:
        elapsed = pipeline.elapsed_s if pipeline is not None else 0.0
        return SupervisorResponse(
            response_id    = str(uuid.uuid4()),
            request_id     = request.request_id,
            supervision_id = request.supervision_id,
            subsystem_id   = request.subsystem_id,
            workflow_type  = request.workflow_type,
            status         = ResponseStatus.FAILURE,
            error_message  = error_message,
            elapsed_s      = elapsed,
            metadata       = dict(metadata or {}),
        )
