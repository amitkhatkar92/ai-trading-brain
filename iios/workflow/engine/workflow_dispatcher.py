"""
workflow_dispatcher.py — iios.workflow.engine
----------------------------------------------
WorkflowDispatcher — coordinates dispatch of a workflow request
through the pipeline.

Does NOT implement business logic, governance, or task execution.
Delegates all stage execution to WorkflowPipeline.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import List, Optional

from iios.common.logging.logging_manager import get_logger

from .workflow_context import WorkflowEngineContext
from .workflow_pipeline import PipelineExecution, WorkflowPipeline
from .workflow_request import WorkflowEngineRequest

_log = get_logger(__name__)


class WorkflowDispatcher:
    """
    Coordinates dispatch of workflow requests through the pipeline.

    Thread-safe.  Each dispatch creates an independent PipelineExecution
    so concurrent dispatches do not interfere.
    """

    def __init__(
        self,
        pipeline: Optional[WorkflowPipeline] = None,
    ) -> None:
        self._pipeline = pipeline or WorkflowPipeline()
        self._lock     = threading.Lock()

    def dispatch(
        self,
        request: WorkflowEngineRequest,
        context: WorkflowEngineContext,
    ) -> PipelineExecution:
        """
        Dispatch a single workflow request through the pipeline.

        Returns:
            PipelineExecution with stage completion results.
        """
        _log.debug(
            f"Dispatcher: dispatch request={request.request_id!r} "
            f"session={context.session_id!r}"
        )
        return self._pipeline.execute(request, context)

    def dispatch_batch(
        self,
        requests: List[WorkflowEngineRequest],
        contexts: List[WorkflowEngineContext],
    ) -> List[PipelineExecution]:
        """
        Dispatch multiple requests in sequence.

        Failures in one request do not affect others.
        """
        results = []
        for req, ctx in zip(requests, contexts):
            execution = self.dispatch(req, ctx)
            results.append(execution)
        return results

    def pipeline(self) -> WorkflowPipeline:
        return self._pipeline

    def stage_count(self) -> int:
        return self._pipeline.stage_count()
