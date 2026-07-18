"""
iios/execution/recovery/engine/recovery_factory.py
==================================================
RecoveryFactory — LifecycleAwareMixin factory for all M2 domain objects.

Creates RecoveryRequest, RecoveryContext, RecoverySnapshot instances.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_SYSTEM,
    FACTORY_ID,
    VERSION,
    PipelineStage,
    RecoveryEngineState,
    RecoveryOutcome,
    RecoveryRequestPriority,
    RecoveryRequestType,
)
from .exceptions import RecoveryEngineNotRunningError
from .recovery_context import (
    ExecutionGatewaySnapshot,
    ExecutionMonitoringSnapshot,
    ExecutionRiskSnapshot,
    FailureContext,
    RecoveryContext,
    make_failure_context,
    make_recovery_context,
)
from .recovery_request import RecoveryRequest, make_recovery_request
from .recovery_response import RecoveryResponse, make_failure_response, make_success_response
from .recovery_snapshot import RecoverySnapshot, make_recovery_snapshot

_log = get_logger(__name__)


class RecoveryFactory(LifecycleAwareMixin):
    """
    Lifecycle-aware factory for M2 domain objects.

    Provides convenience methods to create consistent objects with proper
    defaults and auto-generated IDs.
    """

    def __init__(self) -> None:
        super().__init__()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("RecoveryFactory started.", system_id=FACTORY_ID)

    def _on_stop(self) -> None:
        _log.info("RecoveryFactory stopped.", system_id=FACTORY_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryEngineNotRunningError()

    # ── FailureContext ────────────────────────────────────────────────────────

    def create_failure_context(
        self,
        subsystem_id: str,
        failure_type: str,
        failure_reason: str,
        *,
        severity: str = "MEDIUM",
        affected_components: Tuple[str, ...] = (),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FailureContext:
        self._assert_running()
        return make_failure_context(
            subsystem_id        = subsystem_id,
            failure_type        = failure_type,
            failure_reason      = failure_reason,
            severity            = severity,
            affected_components = affected_components,
            metadata            = metadata,
        )

    # ── RecoveryRequest ───────────────────────────────────────────────────────

    def create_request(
        self,
        execution_session_id: str,
        subsystem_id: str,
        failure_context: FailureContext,
        recovery_reason: str,
        *,
        request_type: RecoveryRequestType     = RecoveryRequestType.AUTOMATIC,
        priority:     RecoveryRequestPriority = RecoveryRequestPriority.NORMAL,
        requester:    str                     = ACTOR_SYSTEM,
        workflow_id:  str                     = "",
        tags:         Tuple[str, ...]         = (),
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> RecoveryRequest:
        self._assert_running()
        return make_recovery_request(
            execution_session_id = execution_session_id,
            subsystem_id         = subsystem_id,
            failure_context      = failure_context,
            recovery_reason      = recovery_reason,
            request_type         = request_type,
            priority             = priority,
            requester            = requester,
            workflow_id          = workflow_id,
            tags                 = tags,
            metadata             = metadata,
        )

    # ── RecoveryContext ───────────────────────────────────────────────────────

    def create_context(
        self,
        request: RecoveryRequest,
        *,
        monitoring_snapshot: Optional[ExecutionMonitoringSnapshot] = None,
        gateway_snapshot: Optional[ExecutionGatewaySnapshot] = None,
        risk_snapshot: Optional[ExecutionRiskSnapshot] = None,
        recovery_plan_id: str = "",
        workflow_id: str = "",
        tags: Tuple[str, ...] = (),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RecoveryContext:
        self._assert_running()
        return make_recovery_context(
            request_id           = request.request_id,
            execution_session_id = request.execution_session_id,
            subsystem_id         = request.subsystem_id,
            failure_context      = request.failure_context,
            monitoring_snapshot  = monitoring_snapshot,
            gateway_snapshot     = gateway_snapshot,
            risk_snapshot        = risk_snapshot,
            recovery_plan_id     = recovery_plan_id,
            workflow_id          = workflow_id or request.workflow_id,
            tags                 = tags or request.tags,
            metadata             = metadata,
        )

    # ── RecoverySnapshot ─────────────────────────────────────────────────────

    def create_snapshot(
        self,
        session_id: str,
        request_id: str,
        subsystem_id: str,
        engine_state: RecoveryEngineState,
        current_stage: Optional[PipelineStage],
        stages_completed: int,
        stages_total: int,
        failure_type: str,
        failure_severity: str,
        failure_reason: str,
        recovery_outcome: RecoveryOutcome,
        *,
        is_complete: bool = False,
        started_at: Optional[float] = None,
        completed_at: Optional[float] = None,
        duration_ms: float = 0.0,
        has_policy_result: bool = False,
        has_failover_result: bool = False,
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RecoverySnapshot:
        self._assert_running()
        return make_recovery_snapshot(
            session_id         = session_id,
            request_id         = request_id,
            subsystem_id       = subsystem_id,
            engine_state       = engine_state,
            current_stage      = current_stage,
            stages_completed   = stages_completed,
            stages_total       = stages_total,
            failure_type       = failure_type,
            failure_severity   = failure_severity,
            failure_reason     = failure_reason,
            recovery_outcome   = recovery_outcome,
            is_complete        = is_complete,
            started_at         = started_at,
            completed_at       = completed_at,
            duration_ms        = duration_ms,
            has_policy_result  = has_policy_result,
            has_failover_result= has_failover_result,
            error_message      = error_message,
            metadata           = metadata,
        )

    # ── RecoveryResponse ─────────────────────────────────────────────────────

    def create_success_response(
        self,
        request_id: str,
        session_id: str,
        subsystem_id: str,
        *,
        started_at: Optional[float] = None,
        completed_at: Optional[float] = None,
        snapshot_id: str = "",
        pipeline_stages_completed: int = 0,
        pipeline_stages_total: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RecoveryResponse:
        self._assert_running()
        return make_success_response(
            request_id                = request_id,
            session_id                = session_id,
            subsystem_id              = subsystem_id,
            started_at                = started_at,
            completed_at              = completed_at,
            snapshot_id               = snapshot_id,
            pipeline_stages_completed = pipeline_stages_completed,
            pipeline_stages_total     = pipeline_stages_total,
            metadata                  = metadata,
        )

    def create_failure_response(
        self,
        request_id: str,
        session_id: str,
        subsystem_id: str,
        error_message: str,
        *,
        started_at: Optional[float] = None,
        completed_at: Optional[float] = None,
        pipeline_stages_completed: int = 0,
        pipeline_stages_total: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RecoveryResponse:
        self._assert_running()
        return make_failure_response(
            request_id                = request_id,
            session_id                = session_id,
            subsystem_id              = subsystem_id,
            error_message             = error_message,
            started_at                = started_at,
            completed_at              = completed_at,
            pipeline_stages_completed = pipeline_stages_completed,
            pipeline_stages_total     = pipeline_stages_total,
            metadata                  = metadata,
        )
