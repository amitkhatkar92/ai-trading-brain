"""
supervisor_manager.py — iios.supervisor.engine
-----------------------------------------------
Internal workflow coordinator for the Supervisor Engine.

THIS IS AN INTERNAL MODULE — NOT PART OF THE PUBLIC API.

Orchestrates the 8-phase supervisor workflow pipeline:
  1. Initialize  — create + initialize session
  2. Discover    — discover subsystems / data sources
  3. Collect     — collect snapshots and health data
  4. Validate    — structural validation
  5. Dispatch    — route to governance frameworks (M3 / M4)
  6. Supervise   — enter supervising or monitoring state
  7. Publish     — build and publish snapshot
  8. Complete    — complete session and close pipeline

NEVER raises.  All exceptions are caught and returned as failure responses.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ENGINE_SYSTEM_ID,
    EngineState,
    PipelineStatus,
    SchedulerPriority,
    SupervisorWorkflowType,
    MONITORING_WORKFLOWS,
)
from .supervisor_pipeline import SupervisorPipeline, PipelineStage
from .supervisor_request import SupervisorRequest
from .supervisor_response import SupervisorEngineSnapshot, SupervisorResponse
from .supervisor_events import (
    make_supervisor_engine_initialized,
    make_supervisor_engine_started,
    make_supervisor_engine_collected,
    make_supervisor_engine_validated,
    make_supervisor_engine_dispatched,
    make_supervisor_engine_monitoring_started,
    make_supervisor_engine_published,
    make_supervisor_engine_completed,
    make_supervisor_engine_failed,
)

_log = get_logger(__name__)


class SupervisorWorkflowManager:
    """
    Runs a complete supervisor workflow pipeline.

    Injected with collaborator components from the engine.  All phases are
    invoked sequentially; a failed phase immediately short-circuits to
    ``_build_failure_response``.

    Parameters
    ----------
    session_manager : Drives lifecycle sessions.
    dispatcher :      Routes to M3 / M4 frameworks.
    factory :         Creates value objects.
    health_reporter : Provides health snapshots.
    statistics :      Accumulates metrics.
    history :         Stores audit records.
    event_listeners : Functions notified on engine events.
    """

    def __init__(
        self,
        session_manager,
        dispatcher,
        factory,
        health_reporter,
        statistics,
        history,
        event_listeners,
    ) -> None:
        self._sm       = session_manager
        self._dsp      = dispatcher
        self._factory  = factory
        self._health   = health_reporter
        self._stats    = statistics
        self._hist     = history
        self._listeners = event_listeners  # mutable list managed by engine

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run_workflow(
        self,
        pipeline: SupervisorPipeline,
        request:  SupervisorRequest,
    ) -> SupervisorResponse:
        """
        Execute the full 8-phase supervisor workflow.

        Never raises.  Returns a SupervisorResponse (success or failure).
        """
        session = None
        pipeline.start()

        try:
            # Phase 1: Initialize
            session = self._phase_initialize(pipeline, request)

            # Phase 2: Discover
            session = self._phase_discover(pipeline, request, session)

            # Phase 3: Collect
            session = self._phase_collect(pipeline, request, session)

            # Phase 4: Validate
            session = self._phase_validate(pipeline, request, session)

            # Phase 5: Dispatch
            next_state = self._phase_dispatch(pipeline, request)

            # Phase 6: Supervise / Monitor
            session = self._phase_supervise_or_monitor(
                pipeline, request, session, next_state
            )

            # Phase 7: Publish
            snapshot = self._phase_publish(pipeline, request, session)

            # Phase 8: Complete
            self._phase_complete(pipeline, request, session)

            response = self._factory.create_success_response(
                request, pipeline, snapshot=snapshot
            )
            self._stats.record_response(success=True)
            self._stats.record_elapsed(pipeline.elapsed_s)
            self._hist.record_response(response)
            return response

        except Exception as exc:           # noqa: BLE001
            return self._build_failure_response(pipeline, request, session, exc)

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def _phase_initialize(self, pipeline, request):
        start = time.time()
        try:
            session = self._sm.create_session(
                request.supervision_id,
                request.subsystem_id,
                metadata={"pipeline_id": pipeline.pipeline_id},
            )
            pipeline.session_id = session.session_id
            session = self._sm.initialize_session(session)
            pipeline.add_stage(PipelineStage(
                stage_name   = "initialize",
                engine_state = EngineState.INITIALIZING,
                status       = PipelineStatus.COMPLETED,
                started_at   = start,
                completed_at = time.time(),
            ))
            event = make_supervisor_engine_initialized(
                request.supervision_id,
                session_id=session.session_id,
            )
            self._hist.record_event(event)
            self._dispatch_event(event)
            self._stats.record_session()
            _log.debug(
                f"[{request.supervision_id}] Phase 1 Initialize complete"
            )
            return session
        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "initialize",
                engine_state = EngineState.INITIALIZING,
                status       = PipelineStatus.FAILED,
                started_at   = start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise

    def _phase_discover(self, pipeline, request, session):
        start = time.time()
        try:
            session = self._sm.discover_session(session)
            pipeline.add_stage(PipelineStage(
                stage_name   = "discover",
                engine_state = EngineState.DISCOVERING,
                status       = PipelineStatus.COMPLETED,
                started_at   = start,
                completed_at = time.time(),
            ))
            event = make_supervisor_engine_started(
                request.supervision_id,
                session_id  = session.session_id,
                pipeline_id = pipeline.pipeline_id,
            )
            self._hist.record_event(event)
            self._dispatch_event(event)
            _log.debug(
                f"[{request.supervision_id}] Phase 2 Discover complete"
            )
            return session
        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "discover",
                engine_state = EngineState.DISCOVERING,
                status       = PipelineStatus.FAILED,
                started_at   = start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise

    def _phase_collect(self, pipeline, request, session):
        start = time.time()
        try:
            # Validate session (transitions DISCOVERING → VALIDATING)
            session = self._sm.validate_session(session)
            self._stats.record_health_check()
            pipeline.add_stage(PipelineStage(
                stage_name   = "collect",
                engine_state = EngineState.COLLECTING,
                status       = PipelineStatus.COMPLETED,
                started_at   = start,
                completed_at = time.time(),
                metadata     = {
                    "input_keys": list(request.inputs.keys()),
                },
            ))
            event = make_supervisor_engine_collected(
                request.supervision_id,
                session_id  = session.session_id,
                pipeline_id = pipeline.pipeline_id,
            )
            self._hist.record_event(event)
            self._dispatch_event(event)
            _log.debug(
                f"[{request.supervision_id}] Phase 3 Collect complete"
            )
            return session
        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "collect",
                engine_state = EngineState.COLLECTING,
                status       = PipelineStatus.FAILED,
                started_at   = start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise

    def _phase_validate(self, pipeline, request, session):
        start = time.time()
        try:
            # mark_ready transitions VALIDATING → READY
            session = self._sm.ready_session(session)
            pipeline.add_stage(PipelineStage(
                stage_name   = "validate",
                engine_state = EngineState.VALIDATING,
                status       = PipelineStatus.COMPLETED,
                started_at   = start,
                completed_at = time.time(),
            ))
            event = make_supervisor_engine_validated(
                request.supervision_id,
                session_id  = session.session_id,
                pipeline_id = pipeline.pipeline_id,
            )
            self._hist.record_event(event)
            self._dispatch_event(event)
            _log.debug(
                f"[{request.supervision_id}] Phase 4 Validate complete"
            )
            return session
        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "validate",
                engine_state = EngineState.VALIDATING,
                status       = PipelineStatus.FAILED,
                started_at   = start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise

    def _phase_dispatch(self, pipeline, request) -> EngineState:
        start = time.time()
        try:
            self._dsp.dispatch(pipeline, request)
            next_state = self._dsp.next_engine_state(request.workflow_type)
            pipeline.add_stage(PipelineStage(
                stage_name   = "dispatch",
                engine_state = EngineState.DISPATCHING,
                status       = PipelineStatus.COMPLETED,
                started_at   = start,
                completed_at = time.time(),
                metadata     = {"next_state": next_state.value},
            ))
            event = make_supervisor_engine_dispatched(
                request.supervision_id,
                pipeline_id = pipeline.pipeline_id,
            )
            self._hist.record_event(event)
            self._dispatch_event(event)
            _log.debug(
                f"[{request.supervision_id}] Phase 5 Dispatch → {next_state.value}"
            )
            return next_state
        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "dispatch",
                engine_state = EngineState.DISPATCHING,
                status       = PipelineStatus.FAILED,
                started_at   = start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise

    def _phase_supervise_or_monitor(self, pipeline, request, session, next_state):
        start = time.time()
        try:
            # Always transition READY → SUPERVISING first
            session = self._sm.supervise_session(session)
            target_state = EngineState.SUPERVISING

            # For monitoring workflows also transition SUPERVISING → MONITORING
            if next_state == EngineState.MONITORING:
                session = self._sm.monitor_session(session)
                target_state = EngineState.MONITORING
                ev = make_supervisor_engine_monitoring_started(
                    request.supervision_id,
                    session_id  = session.session_id,
                    pipeline_id = pipeline.pipeline_id,
                )
                self._hist.record_event(ev)
                self._dispatch_event(ev)

            pipeline.add_stage(PipelineStage(
                stage_name   = "supervise_or_monitor",
                engine_state = target_state,
                status       = PipelineStatus.COMPLETED,
                started_at   = start,
                completed_at = time.time(),
                metadata     = {"target": target_state.value},
            ))
            _log.debug(
                f"[{request.supervision_id}] Phase 6 → {target_state.value}"
            )
            return session
        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "supervise_or_monitor",
                engine_state = next_state,
                status       = PipelineStatus.FAILED,
                started_at   = start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise

    def _phase_publish(
        self,
        pipeline: SupervisorPipeline,
        request:  SupervisorRequest,
        session,
    ) -> SupervisorEngineSnapshot:
        start = time.time()
        try:
            # Determine engine state from final stage
            final_state = EngineState.SUPERVISING
            for stage in reversed(pipeline.stages):
                if stage.engine_state not in (
                    EngineState.PUBLISHING, EngineState.DISPATCHING
                ):
                    final_state = stage.engine_state
                    break

            health   = self._health.report(engine_state=final_state.value)
            snapshot = self._factory.create_snapshot(
                pipeline,
                final_state,
                subsystems_collected=list(request.inputs.keys()),
                health_summary     = health,
                outputs            = {},
            )
            self._stats.record_snapshot()
            pipeline.add_stage(PipelineStage(
                stage_name   = "publish",
                engine_state = EngineState.PUBLISHING,
                status       = PipelineStatus.COMPLETED,
                started_at   = start,
                completed_at = time.time(),
            ))
            event = make_supervisor_engine_published(
                request.supervision_id,
                session_id  = session.session_id,
                pipeline_id = pipeline.pipeline_id,
            )
            self._hist.record_event(event)
            self._dispatch_event(event)
            _log.debug(
                f"[{request.supervision_id}] Phase 7 Publish complete"
            )
            return snapshot
        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "publish",
                engine_state = EngineState.PUBLISHING,
                status       = PipelineStatus.FAILED,
                started_at   = start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise

    def _phase_complete(self, pipeline, request, session) -> None:
        start = time.time()
        try:
            self._sm.complete_session(session)
            pipeline.complete()
            pipeline.add_stage(PipelineStage(
                stage_name   = "complete",
                engine_state = EngineState.COMPLETED,
                status       = PipelineStatus.COMPLETED,
                started_at   = start,
                completed_at = time.time(),
            ))
            event = make_supervisor_engine_completed(
                request.supervision_id,
                session_id  = session.session_id,
                pipeline_id = pipeline.pipeline_id,
            )
            self._hist.record_event(event)
            self._dispatch_event(event)
            _log.debug(
                f"[{request.supervision_id}] Phase 8 Complete"
            )
        except Exception:                  # noqa: BLE001
            # Non-fatal: pipeline result already determined
            pipeline.complete()

    # ------------------------------------------------------------------
    # Failure handling
    # ------------------------------------------------------------------

    def _build_failure_response(
        self,
        pipeline: SupervisorPipeline,
        request:  SupervisorRequest,
        session,
        exc:      Exception,
    ) -> SupervisorResponse:
        error_msg = str(exc)
        try:
            pipeline.fail(error_msg)
        except Exception:          # noqa: BLE001
            pass
        if session is not None:
            try:
                self._sm.fail_session(session, error=error_msg)
            except Exception:      # noqa: BLE001
                pass
        event = make_supervisor_engine_failed(
            request.supervision_id,
            session_id  = session.session_id if session else "",
            pipeline_id = pipeline.pipeline_id,
            error       = error_msg,
        )
        self._hist.record_event(event)
        self._dispatch_event(event)
        self._stats.record_response(success=False)
        self._stats.record_elapsed(pipeline.elapsed_s)
        response = self._factory.create_failure_response(
            request, pipeline, error_message=error_msg
        )
        self._hist.record_response(response)
        _log.warning(
            f"[{request.supervision_id}] Workflow failed: {error_msg}"
        )
        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _dispatch_event(self, event) -> None:
        for fn in list(self._listeners):
            try:
                fn(event)
            except Exception:          # noqa: BLE001
                pass
