"""
integration_pipeline.py — iios.integration.engine
---------------------------------------------------
IntegrationPipeline — coordinates the ordered stages of a single
integration request workflow.

Does NOT implement any connector, adapter, or protocol logic.
All external coordination delegates to M3 (Governance) and M4 (Services).

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    PIPELINE_STAGE_ORDER,
    PipelineStage,
)
from .integration_context import IntegrationEngineContext
from .integration_request import IntegrationRequest

_log = get_logger(__name__)


class PipelineExecution:
    """
    Mutable tracking record for a single pipeline run.

    Records which stages have completed, which failed, and the overall result.
    """

    def __init__(self, request_id: str, session_id: str) -> None:
        self.execution_id:       str                    = f"pipe-{uuid.uuid4().hex[:12]}"
        self.request_id:         str                    = request_id
        self.session_id:         str                    = session_id
        self.current_stage:      Optional[PipelineStage]= None
        self.completed_stages:   List[PipelineStage]    = []
        self.failed_stage:       Optional[PipelineStage]= None
        self.started_at:         str                    = datetime.now(tz=timezone.utc).isoformat()
        self.completed_at:       Optional[str]          = None
        self.success:            bool                   = False
        self.error_message:      str                    = ""

    def mark_stage_started(self, stage: PipelineStage) -> None:
        self.current_stage = stage

    def mark_stage_complete(self, stage: PipelineStage) -> None:
        self.completed_stages.append(stage)
        self.current_stage = None

    def mark_failed(self, stage: PipelineStage, error: str) -> None:
        self.failed_stage   = stage
        self.error_message  = error
        self.success        = False
        self.completed_at   = datetime.now(tz=timezone.utc).isoformat()

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
            "started_at":       self.started_at,
            "completed_at":     self.completed_at,
            "success":          self.success,
            "error_message":    self.error_message,
        }


class IntegrationPipeline:
    """
    Coordinates the ordered execution of pipeline stages.

    Each stage is a coordination point — the pipeline does NOT perform
    connector logic, protocol communication, or business processing.

    Stage handlers are called in PIPELINE_STAGE_ORDER.
    Unknown or missing handlers are treated as no-ops.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def execute(
        self,
        request:    IntegrationRequest,
        context:    IntegrationEngineContext,
    ) -> PipelineExecution:
        """
        Run the pipeline for a request.

        Executes all stages in order.  A stage failure marks the execution
        as failed and stops further processing.

        Returns:
            PipelineExecution with the result.
        """
        execution = PipelineExecution(
            request_id = request.request_id,
            session_id = context.session_id,
        )
        _log.debug(
            f"Pipeline starting: "
            f"exec={execution.execution_id!r} "
            f"request={request.request_id!r}"
        )

        for stage in PIPELINE_STAGE_ORDER:
            execution.mark_stage_started(stage)
            try:
                self._run_stage(stage, request, context, execution)
                execution.mark_stage_complete(stage)
            except Exception as exc:
                execution.mark_failed(stage, str(exc))
                _log.warning(
                    f"Pipeline stage failed: "
                    f"exec={execution.execution_id!r} "
                    f"stage={stage.value!r} "
                    f"error={exc!r}"
                )
                return execution

        execution.mark_complete()
        _log.debug(
            f"Pipeline complete: exec={execution.execution_id!r}"
        )
        return execution

    def _run_stage(
        self,
        stage:     PipelineStage,
        request:   IntegrationRequest,
        context:   IntegrationEngineContext,
        execution: PipelineExecution,
    ) -> None:
        """
        Execute a single pipeline stage.

        All stages are coordination points.  They delegate to subsystems
        that are injected at the engine level.  The pipeline itself has
        no dependencies on connectors, protocols, or external systems.
        """
        # Each stage is a designated coordination point.
        # The pipeline records progress; actual work is dispatched by the engine.
        if stage == PipelineStage.VALIDATE:
            self._stage_validate(request, context)
        elif stage == PipelineStage.INITIALIZE:
            self._stage_initialize(request, context)
        elif stage == PipelineStage.LOAD_CONNECTOR:
            self._stage_load_connector(request, context)
        elif stage == PipelineStage.LOAD_ADAPTER:
            self._stage_load_adapter(request, context)
        elif stage == PipelineStage.VALIDATE_PROTOCOL:
            self._stage_validate_protocol(request, context)
        elif stage == PipelineStage.DISPATCH:
            self._stage_dispatch(request, context)
        elif stage == PipelineStage.COORDINATE_GOVERNANCE:
            self._stage_coordinate_governance(request, context)
        elif stage == PipelineStage.COORDINATE_SERVICES:
            self._stage_coordinate_services(request, context)
        elif stage == PipelineStage.PUBLISH:
            self._stage_publish(request, context)
        elif stage == PipelineStage.COMPLETE:
            self._stage_complete(request, context)

    # ----------------------------------------------------------------
    # Stage coordination points (no-op implementations)
    # All real work is coordinated by the engine or delegated to M3/M4.
    # ----------------------------------------------------------------

    def _stage_validate(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Validation runs in the engine before pipeline

    def _stage_initialize(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Session initialized by IntegrationSessionManager before pipeline

    def _stage_load_connector(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Connector resolved by engine from IntegrationEngineRegistry

    def _stage_load_adapter(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Adapter resolved by engine from IntegrationEngineRegistry

    def _stage_validate_protocol(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Protocol validated by engine from IntegrationEngineRegistry

    def _stage_dispatch(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Dispatch delegated to M4 Integration Services Framework

    def _stage_coordinate_governance(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Delegated to M3 Integration Governance Policy Framework

    def _stage_coordinate_services(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Delegated to M4 Integration Services Framework

    def _stage_publish(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Snapshot published by engine

    def _stage_complete(self, req: IntegrationRequest, ctx: IntegrationEngineContext) -> None:
        pass   # Session completed by engine via IntegrationSessionManager
