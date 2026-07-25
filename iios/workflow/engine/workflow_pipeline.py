"""
workflow_pipeline.py — iios.workflow.engine
--------------------------------------------
WorkflowPipeline — coordinates the ordered stages of a single
workflow execution.

Does NOT implement any business logic, governance evaluation,
or orchestration.  All external coordination delegates to:
  - M3 Governance Policy Framework (GOVERN stage hook)
  - M4 Orchestration Framework (ORCHESTRATE stage hook)

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import PIPELINE_STAGE_ORDER, WorkflowPipelineStage
from .workflow_context import WorkflowEngineContext
from .workflow_request import WorkflowEngineRequest

_log = get_logger(__name__)

StageHandler = Callable[
    ["WorkflowEngineRequest", "WorkflowEngineContext"],
    Optional[Dict[str, Any]],
]


class PipelineExecution:
    """
    Mutable tracking record for a single workflow pipeline run.

    Records which stages have completed, which failed, and the overall result.
    """

    def __init__(self, request_id: str, session_id: str) -> None:
        self.execution_id:     str                         = f"wpipe-{uuid.uuid4().hex[:10]}"
        self.request_id:       str                         = request_id
        self.session_id:       str                         = session_id
        self.current_stage:    Optional[WorkflowPipelineStage] = None
        self.completed_stages: List[WorkflowPipelineStage]    = []
        self.failed_stage:     Optional[WorkflowPipelineStage]= None
        self.stage_results:    Dict[str, Any]              = {}
        self.started_at:       str                         = datetime.now(tz=timezone.utc).isoformat()
        self.completed_at:     Optional[str]               = None
        self.success:          bool                        = False
        self.error_message:    str                         = ""

    def mark_stage_started(self, stage: WorkflowPipelineStage) -> None:
        self.current_stage = stage

    def mark_stage_complete(
        self,
        stage:  WorkflowPipelineStage,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.completed_stages.append(stage)
        if result:
            self.stage_results[stage.value] = result
        self.current_stage = None

    def mark_failed(self, stage: WorkflowPipelineStage, error: str) -> None:
        self.failed_stage  = stage
        self.error_message = error
        self.success       = False
        self.completed_at  = datetime.now(tz=timezone.utc).isoformat()

    def mark_complete(self) -> None:
        self.success      = True
        self.completed_at = datetime.now(tz=timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id":     self.execution_id,
            "request_id":       self.request_id,
            "session_id":       self.session_id,
            "current_stage":    self.current_stage.value if self.current_stage else None,
            "completed_stages": [s.value for s in self.completed_stages],
            "failed_stage":     self.failed_stage.value if self.failed_stage else None,
            "stage_results":    self.stage_results,
            "started_at":       self.started_at,
            "completed_at":     self.completed_at,
            "success":          self.success,
            "error_message":    self.error_message,
        }


class WorkflowPipeline:
    """
    Coordinates the ordered execution of 8 pipeline stages.

    Each stage is a coordination point.  Stage handlers can be
    registered for specific stages; missing handlers are treated as no-ops.

    GOVERN and ORCHESTRATE stages are hooks — they coordinate M3 and M4
    without implementing their logic.
    """

    def __init__(self) -> None:
        self._handlers: Dict[WorkflowPipelineStage, StageHandler] = {}
        self._lock = threading.Lock()

    # ----------------------------------------------------------------
    # Handler registration
    # ----------------------------------------------------------------

    def register_handler(
        self,
        stage:   WorkflowPipelineStage,
        handler: StageHandler,
    ) -> None:
        with self._lock:
            self._handlers[stage] = handler

    def registered_stages(self) -> List[WorkflowPipelineStage]:
        with self._lock:
            return list(self._handlers.keys())

    # ----------------------------------------------------------------
    # Execute
    # ----------------------------------------------------------------

    def execute(
        self,
        request: WorkflowEngineRequest,
        context: WorkflowEngineContext,
    ) -> PipelineExecution:
        """
        Run the pipeline for a request.

        Executes all 8 stages in PIPELINE_STAGE_ORDER.
        A stage failure marks the execution as failed and stops further processing.

        Returns:
            PipelineExecution with the result.
        """
        execution = PipelineExecution(
            request_id = request.request_id,
            session_id = context.session_id,
        )
        _log.debug(
            f"Pipeline starting: exec={execution.execution_id!r} "
            f"request={request.request_id!r}"
        )

        with self._lock:
            handlers = dict(self._handlers)

        for stage in PIPELINE_STAGE_ORDER:
            execution.mark_stage_started(stage)
            handler = handlers.get(stage)
            try:
                result = handler(request, context, execution) if handler else None
                execution.mark_stage_complete(stage, result)
                _log.debug(
                    f"Pipeline stage complete: {stage.value!r} "
                    f"exec={execution.execution_id!r}"
                )
            except Exception as exc:
                execution.mark_failed(stage, str(exc))
                _log.warning(
                    f"Pipeline stage failed: {stage.value!r} "
                    f"exec={execution.execution_id!r} error={exc!r}"
                )
                return execution

        execution.mark_complete()
        return execution

    def stage_count(self) -> int:
        with self._lock:
            return len(self._handlers)
