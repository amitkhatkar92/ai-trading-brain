"""
iios/execution/recovery/engine/recovery_manager.py
==================================================
RecoveryManager — internal coordinator for the Execution Recovery Engine.

Owns all sub-components and orchestrates the full recovery workflow:
  Request → Validate → Context → Session → Pipeline → Dispatch → Verify →
  Snapshot → Response

The manager does NOT determine policies and does NOT execute failover.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from iios.execution.recovery.lifecycle import RecoverySession

from .constants import (
    ACTOR_MANAGER,
    ACTOR_POLICY,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    MANAGER_ID,
    PIPELINE_STAGES_ORDERED,
    VERSION,
    PipelineStage,
    RecoveryEngineState,
    RecoveryOutcome,
    RecoveryResponseStatus,
)
from .exceptions import (
    RecoveryContextValidationError,
    RecoveryEngineNotRunningError,
    RecoveryRequestValidationError,
)
from .recovery_context import RecoveryContext, make_recovery_context
from .recovery_dispatcher import (
    DispatchResult,
    FailoverFrameworkPort,
    PolicyFrameworkPort,
    RecoveryDispatcher,
)
from .recovery_events import (
    RecoveryEngineEvent,
    make_engine_started,
    make_engine_stopped,
    make_failure_detected,
    make_recovery_completed,
    make_recovery_dispatched,
    make_recovery_failed,
    make_recovery_initialized,
    make_recovery_started,
    make_recovery_stopped,
    make_recovery_verified,
)
from .recovery_factory import RecoveryFactory
from .recovery_history import RecoveryEngineHistory
from .recovery_pipeline import RecoveryPipeline
from .recovery_registry import RecoveryRegistry
from .recovery_request import RecoveryRequest
from .recovery_response import RecoveryResponse
from .recovery_scheduler import RecoveryScheduler
from .recovery_session_manager import RecoverySessionManager
from .recovery_snapshot import RecoverySnapshot
from .recovery_statistics import RecoveryEngineStatistics
from .recovery_validation import RecoveryEngineValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class RecoveryManager(LifecycleAwareMixin):
    """
    Internal coordinator for the Execution Recovery Engine.

    Orchestrates the complete recovery workflow and coordinates all
    sub-components.  All methods are thread-safe.
    """

    def __init__(
        self,
        max_requests:       int                                  = DEFAULT_MAX_REQUESTS,
        max_history:        int                                  = DEFAULT_MAX_HISTORY,
        max_concurrent:     int                                  = DEFAULT_MAX_CONCURRENT,
        policy_framework:   Optional[PolicyFrameworkPort]        = None,
        failover_framework: Optional[FailoverFrameworkPort]      = None,
        lifecycle:          Optional[Any]                        = None,
    ) -> None:
        super().__init__()
        self._session_manager = RecoverySessionManager(lifecycle=lifecycle)
        self._registry        = RecoveryRegistry(max_requests=max_requests)
        self._scheduler       = RecoveryScheduler()
        self._dispatcher      = RecoveryDispatcher(policy_framework, failover_framework)
        self._factory         = RecoveryFactory()
        self._validator       = RecoveryEngineValidator()
        self._stats           = RecoveryEngineStatistics()
        self._history         = RecoveryEngineHistory(
            max_requests  = max_history,
            max_responses = max_history,
            max_events    = max_history * 10,
            max_snapshots = max_history,
        )
        self._listeners:       List[Callable[[RecoveryEngineEvent], None]] = []
        self._listeners_lock   = threading.Lock()
        self._semaphore        = threading.Semaphore(max(1, max_concurrent))

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._factory.start()
        self._registry.start()
        self._scheduler.start()
        self._dispatcher.start()
        self._session_manager.start()
        _audit.log_lifecycle_event(MANAGER_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("RecoveryManager started.", system_id=MANAGER_ID, version=VERSION)

    def _on_stop(self) -> None:
        self._session_manager.stop()
        self._dispatcher.stop()
        self._scheduler.stop()
        self._registry.stop()
        self._factory.stop()
        _audit.log_lifecycle_event(MANAGER_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("RecoveryManager stopped.", system_id=MANAGER_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryEngineNotRunningError()

    # ── Event emission ────────────────────────────────────────────────────────

    def _emit(self, event: RecoveryEngineEvent) -> None:
        self._history.append_event(event)
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    "RecoveryEngineEvent listener raised.",
                    event_type=event.event_type.value,
                    error=str(exc),
                )

    # ── Listener management ───────────────────────────────────────────────────

    def add_event_listener(self, listener: Callable[[RecoveryEngineEvent], None]) -> None:
        with self._listeners_lock:
            self._listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[RecoveryEngineEvent], None]) -> None:
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l != listener]

    # ── Port injection ────────────────────────────────────────────────────────

    def set_policy_framework(self, port: PolicyFrameworkPort) -> None:
        self._dispatcher.set_policy_framework(port)

    def set_failover_framework(self, port: FailoverFrameworkPort) -> None:
        self._dispatcher.set_failover_framework(port)

    # ── Main workflow ─────────────────────────────────────────────────────────

    def start_recovery(self, request: RecoveryRequest) -> RecoveryResponse:
        """
        Orchestrate a complete recovery workflow for the given request.

        Thread-safe; limits concurrency via semaphore.
        Returns a RecoveryResponse whether the workflow succeeds or fails.
        """
        self._assert_running()
        self._stats.record_request()
        self._history.append_request(request)

        acquired = self._semaphore.acquire(blocking=True, timeout=5.0)
        if not acquired:
            error = "Recovery concurrency limit exceeded — request rejected"
            _log.warning(error, request_id=request.request_id)
            response = self._factory.create_failure_response(
                request_id   = request.request_id,
                session_id   = "",
                subsystem_id = request.subsystem_id,
                error_message = error,
            )
            self._history.append_response(response)
            self._stats.record_failed()
            return response

        try:
            return self._run_workflow(request)
        finally:
            self._semaphore.release()

    def _run_workflow(self, request: RecoveryRequest) -> RecoveryResponse:
        """Execute the full 10-stage pipeline."""
        pipeline   = RecoveryPipeline(request.request_id, "")
        started_at = time.time()
        session_id = ""

        # ── STAGE 1: VALIDATE_CONTEXT ─────────────────────────────────────────
        pipeline.start_stage(PipelineStage.VALIDATE_CONTEXT)
        req_validation = self._validator.validate_request(request)
        if not req_validation.is_valid:
            pipeline.fail_stage(PipelineStage.VALIDATE_CONTEXT, "; ".join(req_validation.errors))
            err = f"Request validation failed: {'; '.join(req_validation.errors)}"
            _log.warning(err, request_id=request.request_id)
            response = self._factory.create_failure_response(
                request.request_id, "", request.subsystem_id, err,
                started_at=started_at,
                pipeline_stages_completed=pipeline.stages_completed,
                pipeline_stages_total=pipeline.stages_total,
            )
            self._history.append_response(response)
            self._stats.record_failed()
            return response
        pipeline.complete_stage(PipelineStage.VALIDATE_CONTEXT)

        # Build context
        context = self._factory.create_context(request)
        ctx_validation = self._validator.validate_context(context)
        if not ctx_validation.is_valid:
            err = f"Context validation failed: {'; '.join(ctx_validation.errors)}"
            pipeline.fail_stage(PipelineStage.VALIDATE_CONTEXT, err)
            response = self._factory.create_failure_response(
                request.request_id, "", request.subsystem_id, err,
                started_at=started_at,
                pipeline_stages_completed=pipeline.stages_completed,
                pipeline_stages_total=pipeline.stages_total,
            )
            self._history.append_response(response)
            self._stats.record_failed()
            return response

        # Store request in registry
        self._registry.store(request)

        # ── STAGE 2: INITIALIZE_SESSION ───────────────────────────────────────
        pipeline.start_stage(PipelineStage.INITIALIZE_SESSION)
        try:
            m1_session = self._session_manager.create_session(request, context)
            session_id = m1_session.session_id
            # Update pipeline with session_id
            pipeline._session_id = session_id
            self._session_manager.initialize(request.request_id, actor=ACTOR_MANAGER)
            self._stats.record_initiated()
            self._stats.record_transition()
        except Exception as exc:
            err = f"Session initialization failed: {exc}"
            pipeline.fail_stage(PipelineStage.INITIALIZE_SESSION, err)
            self._registry.archive(request.request_id)
            response = self._factory.create_failure_response(
                request.request_id, session_id, request.subsystem_id, err,
                started_at=started_at,
                pipeline_stages_completed=pipeline.stages_completed,
                pipeline_stages_total=pipeline.stages_total,
            )
            self._history.append_response(response)
            self._stats.record_failed()
            return response
        pipeline.complete_stage(PipelineStage.INITIALIZE_SESSION)
        self._emit(make_recovery_initialized(
            request.request_id, session_id, actor=ACTOR_MANAGER
        ))

        # ── STAGE 3: ASSESS_FAILURE ───────────────────────────────────────────
        pipeline.start_stage(PipelineStage.ASSESS_FAILURE)
        try:
            self._session_manager.detect(request.request_id, actor=ACTOR_MANAGER)
            self._stats.record_transition()
            self._session_manager.assess(request.request_id, actor=ACTOR_MANAGER)
            self._stats.record_transition()
        except Exception as exc:
            err = f"Failure assessment failed: {exc}"
            pipeline.fail_stage(PipelineStage.ASSESS_FAILURE, err)
            self._session_manager.fail(request.request_id, err, actor=ACTOR_MANAGER)
            response = self._finish_failed(request, session_id, pipeline, started_at, err)
            return response
        pipeline.complete_stage(PipelineStage.ASSESS_FAILURE)
        self._emit(make_failure_detected(
            request.request_id, session_id, actor=ACTOR_MANAGER,
            reason=request.failure_context.failure_reason,
        ))

        # ── STAGE 4: PLAN_RECOVERY ────────────────────────────────────────────
        pipeline.start_stage(PipelineStage.PLAN_RECOVERY)
        try:
            self._session_manager.ready(request.request_id, actor=ACTOR_MANAGER)
            self._stats.record_transition()
        except Exception as exc:
            err = f"Recovery planning failed: {exc}"
            pipeline.fail_stage(PipelineStage.PLAN_RECOVERY, err)
            self._session_manager.fail(request.request_id, err, actor=ACTOR_MANAGER)
            response = self._finish_failed(request, session_id, pipeline, started_at, err)
            return response
        pipeline.complete_stage(PipelineStage.PLAN_RECOVERY)

        # ── STAGE 5: DISPATCH_WORKFLOW ────────────────────────────────────────
        pipeline.start_stage(PipelineStage.DISPATCH_WORKFLOW)
        try:
            self._session_manager.begin_recovery(request.request_id, actor=ACTOR_MANAGER)
            self._stats.record_transition()
        except Exception as exc:
            err = f"Recovery dispatch setup failed: {exc}"
            pipeline.fail_stage(PipelineStage.DISPATCH_WORKFLOW, err)
            self._session_manager.fail(request.request_id, err, actor=ACTOR_MANAGER)
            response = self._finish_failed(request, session_id, pipeline, started_at, err)
            return response
        pipeline.complete_stage(PipelineStage.DISPATCH_WORKFLOW)
        self._emit(make_recovery_started(request.request_id, session_id, actor=ACTOR_MANAGER))

        # ── STAGE 6: COORDINATE_POLICIES ─────────────────────────────────────
        pipeline.start_stage(PipelineStage.COORDINATE_POLICIES)
        dispatch_result: Optional[DispatchResult] = None
        try:
            dispatch_result = self._dispatcher.dispatch(request, context)
            pipeline.complete_stage(PipelineStage.COORDINATE_POLICIES, result=dispatch_result)
        except Exception as exc:
            err = f"Policy coordination failed: {exc}"
            pipeline.fail_stage(PipelineStage.COORDINATE_POLICIES, err)
            self._session_manager.fail(request.request_id, err, actor=ACTOR_MANAGER)
            response = self._finish_failed(request, session_id, pipeline, started_at, err)
            return response
        self._emit(make_recovery_dispatched(
            request.request_id, session_id, actor=ACTOR_MANAGER
        ))

        # If policy rejected recovery, abort
        if dispatch_result and not dispatch_result.dispatched:
            err = "Recovery rejected by policy framework"
            pipeline.fail_stage(PipelineStage.COORDINATE_FAILOVER, err)
            self._session_manager.abort(request.request_id, err, actor=ACTOR_POLICY)
            response = self._finish_failed(
                request, session_id, pipeline, started_at, err,
                status=RecoveryResponseStatus.CANCELLED,
                outcome=RecoveryOutcome.ABORTED,
            )
            return response

        # ── STAGE 7: COORDINATE_FAILOVER ──────────────────────────────────────
        pipeline.start_stage(PipelineStage.COORDINATE_FAILOVER)
        has_failover = dispatch_result is not None and dispatch_result.failover_result is not None
        pipeline.complete_stage(
            PipelineStage.COORDINATE_FAILOVER,
            result=dispatch_result.failover_result if dispatch_result else None,
        )

        # ── STAGE 8: VERIFY_RESULT ────────────────────────────────────────────
        pipeline.start_stage(PipelineStage.VERIFY_RESULT)
        try:
            self._session_manager.verify(request.request_id, actor=ACTOR_MANAGER)
            self._stats.record_transition()
            self._session_manager.complete(request.request_id, actor=ACTOR_MANAGER)
            self._stats.record_transition()
            self._stats.record_verification(successful=True)
        except Exception as exc:
            err = f"Verification failed: {exc}"
            pipeline.fail_stage(PipelineStage.VERIFY_RESULT, err)
            self._session_manager.fail(request.request_id, err, actor=ACTOR_MANAGER)
            self._stats.record_verification(successful=False)
            response = self._finish_failed(request, session_id, pipeline, started_at, err)
            return response
        pipeline.complete_stage(PipelineStage.VERIFY_RESULT)
        self._emit(make_recovery_verified(request.request_id, session_id, actor=ACTOR_MANAGER))

        # ── STAGE 9: PUBLISH_SNAPSHOT ─────────────────────────────────────────
        pipeline.start_stage(PipelineStage.PUBLISH_SNAPSHOT)
        m1_session = self._session_manager.get_session_for_request(request.request_id)
        duration_ms = (m1_session.duration_ms if m1_session else 0.0)
        snapshot = self._factory.create_snapshot(
            session_id        = session_id,
            request_id        = request.request_id,
            subsystem_id      = request.subsystem_id,
            engine_state      = RecoveryEngineState.COMPLETED,
            current_stage     = PipelineStage.PUBLISH_SNAPSHOT,
            stages_completed  = pipeline.stages_completed + 1,
            stages_total      = pipeline.stages_total,
            failure_type      = request.failure_context.failure_type,
            failure_severity  = request.failure_context.severity,
            failure_reason    = request.failure_context.failure_reason,
            recovery_outcome  = RecoveryOutcome.RECOVERED,
            is_complete       = True,
            started_at        = m1_session.start_time if m1_session else started_at,
            completed_at      = m1_session.end_time if m1_session else time.time(),
            duration_ms       = duration_ms,
            has_policy_result = dispatch_result is not None,
            has_failover_result = has_failover,
        )
        self._history.append_snapshot(snapshot)
        pipeline.complete_stage(PipelineStage.PUBLISH_SNAPSHOT, result=snapshot.snapshot_id)

        # ── STAGE 10: FINALIZE ────────────────────────────────────────────────
        pipeline.start_stage(PipelineStage.FINALIZE)
        try:
            self._session_manager.archive(request.request_id, actor=ACTOR_MANAGER)
            self._registry.archive(request.request_id)
        except Exception:
            pass   # archiving is best-effort
        pipeline.complete_stage(PipelineStage.FINALIZE)

        # Build success response
        end_time = time.time()
        total_duration = (end_time - started_at) * 1000.0
        self._stats.record_completed(total_duration)
        response = self._factory.create_success_response(
            request_id                = request.request_id,
            session_id                = session_id,
            subsystem_id              = request.subsystem_id,
            started_at                = started_at,
            completed_at              = end_time,
            snapshot_id               = snapshot.snapshot_id,
            pipeline_stages_completed = pipeline.stages_completed,
            pipeline_stages_total     = pipeline.stages_total,
        )
        self._history.append_response(response)
        self._emit(make_recovery_completed(
            request.request_id, session_id, actor=ACTOR_MANAGER
        ))
        _log.info(
            "Recovery workflow completed.",
            request_id  = request.request_id,
            session_id  = session_id,
            duration_ms = total_duration,
        )
        return response

    def _finish_failed(
        self,
        request:    RecoveryRequest,
        session_id: str,
        pipeline:   RecoveryPipeline,
        started_at: float,
        error:      str,
        *,
        status:  RecoveryResponseStatus = RecoveryResponseStatus.FAILED,
        outcome: RecoveryOutcome        = RecoveryOutcome.UNRECOVERABLE,
    ) -> RecoveryResponse:
        """Build and record a failure response."""
        self._stats.record_failed()
        try:
            self._registry.archive(request.request_id)
        except Exception:
            pass
        response = self._factory.create_failure_response(
            request_id                = request.request_id,
            session_id                = session_id,
            subsystem_id              = request.subsystem_id,
            error_message             = error,
            started_at                = started_at,
            pipeline_stages_completed = pipeline.stages_completed,
            pipeline_stages_total     = pipeline.stages_total,
        )
        self._history.append_response(response)
        self._emit(make_recovery_failed(
            request.request_id, session_id, actor=ACTOR_MANAGER, reason=error
        ))
        _log.warning(
            "Recovery workflow failed.",
            request_id=request.request_id,
            session_id=session_id,
            error=error,
        )
        return response

    # ── Stop recovery ─────────────────────────────────────────────────────────

    def stop_recovery(self, request_id: str, reason: str, *, actor: str = ACTOR_MANAGER) -> None:
        """Abort an in-progress recovery session."""
        self._assert_running()
        self._session_manager.abort(request_id, reason, actor=actor)
        try:
            self._registry.archive(request_id)
        except Exception:
            pass
        self._stats.record_cancelled()
        self._emit(make_recovery_stopped(request_id, "", actor=actor, reason=reason))

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_session_for_request(
        self, request_id: str
    ) -> Optional[RecoverySession]:
        return self._session_manager.get_session_for_request(request_id)

    def active_sessions(self) -> List[RecoverySession]:
        return self._session_manager.active_sessions()

    def statistics(self) -> RecoveryEngineStatistics:
        return self._stats.copy()

    def history(self) -> RecoveryEngineHistory:
        return self._history

    def scheduler(self) -> RecoveryScheduler:
        return self._scheduler

    def registry(self) -> RecoveryRegistry:
        return self._registry
