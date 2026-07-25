"""
workflow_factory.py — iios.workflow.engine
-------------------------------------------
WorkflowEngineFactory — creates engine data objects with defaults.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.workflow.lifecycle import WorkflowType

from .constants import DEFAULT_ENGINE_ID, DEFAULT_PRIORITY, WorkflowDispatchMode
from .workflow_context import WorkflowEngineContext
from .workflow_request import WorkflowEngineRequest
from .workflow_response import WorkflowEngineResponse

_log = get_logger(__name__)


class WorkflowEngineFactory:
    """Creates Workflow Engine data objects with consistent defaults."""

    # ----------------------------------------------------------------
    # Request
    # ----------------------------------------------------------------

    def create_request(
        self,
        workflow_id:   str,
        workflow_type: WorkflowType         = WorkflowType.SEQUENTIAL,
        dispatch_mode: WorkflowDispatchMode = WorkflowDispatchMode.IMMEDIATE,
        *,
        priority:         int                       = DEFAULT_PRIORITY,
        enterprise_id:    str                       = "iios",
        payload:          Optional[Dict[str, Any]]  = None,
        configuration:    Optional[Dict[str, Any]]  = None,
        platform_context: Optional[Dict[str, Any]]  = None,
        session_config:   Optional[Dict[str, Any]]  = None,
        metadata:         Optional[Dict[str, Any]]  = None,
        request_id:       Optional[str]             = None,
    ) -> WorkflowEngineRequest:
        return WorkflowEngineRequest.create(
            workflow_id      = workflow_id,
            workflow_type    = workflow_type,
            dispatch_mode    = dispatch_mode,
            priority         = priority,
            enterprise_id    = enterprise_id,
            payload          = payload,
            configuration    = configuration,
            platform_context = platform_context,
            session_config   = session_config,
            metadata         = metadata,
            request_id       = request_id,
        )

    def create_immediate_request(
        self,
        workflow_id:   str,
        workflow_type: WorkflowType = WorkflowType.SEQUENTIAL,
        **kwargs,
    ) -> WorkflowEngineRequest:
        return self.create_request(
            workflow_id,
            workflow_type,
            WorkflowDispatchMode.IMMEDIATE,
            **kwargs,
        )

    def create_scheduled_request(
        self,
        workflow_id:   str,
        workflow_type: WorkflowType = WorkflowType.SCHEDULED,
        **kwargs,
    ) -> WorkflowEngineRequest:
        return self.create_request(
            workflow_id,
            workflow_type,
            WorkflowDispatchMode.SCHEDULED,
            **kwargs,
        )

    def create_batch_request(
        self,
        workflow_id:   str,
        workflow_type: WorkflowType = WorkflowType.BATCH,
        **kwargs,
    ) -> WorkflowEngineRequest:
        return self.create_request(
            workflow_id,
            workflow_type,
            WorkflowDispatchMode.BATCH,
            **kwargs,
        )

    # ----------------------------------------------------------------
    # Context
    # ----------------------------------------------------------------

    def create_context(
        self,
        request:    WorkflowEngineRequest,
        session_id: str,
        engine_id:  str = DEFAULT_ENGINE_ID,
    ) -> WorkflowEngineContext:
        return WorkflowEngineContext.create(
            request,
            session_id,
            engine_id=engine_id,
        )

    # ----------------------------------------------------------------
    # Response
    # ----------------------------------------------------------------

    def create_success_response(
        self,
        request:    WorkflowEngineRequest,
        session_id: str,
        **kwargs,
    ) -> WorkflowEngineResponse:
        return WorkflowEngineResponse.success_for(
            request, session_id, **kwargs
        )

    def create_failure_response(
        self,
        request:       WorkflowEngineRequest,
        session_id:    str,
        error_message: str,
        **kwargs,
    ) -> WorkflowEngineResponse:
        return WorkflowEngineResponse.failure_for(
            request, session_id, error_message, **kwargs
        )
