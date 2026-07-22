"""
risk_manager.py — iios.risk.engine
=====================================
Internal workflow coordinator for the Risk Engine.

**NOT a public interface.**  Only ``RiskEngine`` may call this class.

Drives a single risk pipeline through seven sequential phases:
  1. Initialize
  2. Collect
  3. Validate (structural)
  4. Dispatch
  5. Assess or Monitor (routing determined by workflow type)
  6. Publish
  7. Complete

Each phase records a :class:`~.risk_pipeline.PipelineStage` on the
pipeline and emits a :class:`~.risk_events.RiskEngineEvent` into history.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    EngineState,
    PipelineStatus,
    ASSESSMENT_WORKFLOWS,
    MONITORING_WORKFLOWS,
)
from .risk_context import RiskEngineContext
from .risk_events import (
    make_risk_initialized,
    make_risk_started,
    make_risk_collected,
    make_risk_dispatched,
    make_risk_assessment_started,
    make_risk_published,
    make_risk_completed,
    make_risk_failed,
)
from .risk_factory import RiskEngineFactory
from .risk_history import RiskEngineHistory
from .risk_pipeline import RiskPipeline, PipelineStage
from .risk_registry import RiskEngineRegistry
from .risk_request import RiskRequest
from .risk_response import RiskEngineSnapshot, RiskResponse
from .risk_dispatcher import RiskDispatcher
from .risk_session_manager import RiskSessionManager
from .risk_statistics import RiskEngineStatistics
from .risk_validation import RiskEngineValidator
from .exceptions import (
    RiskEngineValidationError,
    RiskSessionError,
    RiskCollectionError,
    RiskDispatchError,
)

_log = get_logger(__name__)


class RiskManager:
    """
    Internal workflow coordinator.

    Parameters
    ----------
    session_manager : RiskSessionManager wrapping M1 lifecycle.
    dispatcher :      RiskDispatcher holding M3/M4 hooks.
    registry :        RiskEngineRegistry.
    factory :         RiskEngineFactory.
    validator :       RiskEngineValidator.
    statistics :      RiskEngineStatistics.
    history :         RiskEngineHistory.
    listener_fn :     Callable to dispatch events to external listeners.
    """

    def __init__(
        self,
        session_manager: RiskSessionManager,
        dispatcher:      RiskDispatcher,
        registry:        RiskEngineRegistry,
        factory:         RiskEngineFactory,
        validator:       RiskEngineValidator,
        statistics:      RiskEngineStatistics,
        history:         RiskEngineHistory,
        listener_fn:     Optional[Callable] = None,
    ) -> None:
        self._session_manager = session_manager
        self._dispatcher      = dispatcher
        self._registry        = registry
        self._factory         = factory
        self._validator       = validator
        self._stats           = statistics
        self._history         = history
        self._dispatch_ev     = listener_fn or (lambda ev: None)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run_workflow(
        self,
        pipeline: RiskPipeline,
        request:  RiskRequest,
    ) -> RiskResponse:
        """
        Execute all seven workflow phases and return the response.

        Never raises — all failures are caught and returned as a failure
        :class:`RiskResponse`.
        """
        started = time.time()
        session = None

        try:
            # ── Phase 1: Initialize ────────────────────────────────────
            session = self._phase_initialize(pipeline, request)

            # ── Phase 2: Collect ──────────────────────────────────────
            session = self._phase_collect(pipeline, request, session)

            # ── Phase 3: Validate ─────────────────────────────────────
            session = self._phase_validate(pipeline, request, session)

            # ── Phase 4: Dispatch ─────────────────────────────────────
            next_state = self._phase_dispatch(pipeline, request)

            # ── Phase 5: Assess or Monitor ────────────────────────────
            session = self._phase_assess_or_monitor(pipeline, request, session, next_state)

            # ── Phase 6: Publish ──────────────────────────────────────
            snapshot = self._phase_publish(pipeline, request, session)

            # ── Phase 7: Complete ─────────────────────────────────────
            self._phase_complete(pipeline, request, session)

            elapsed = time.time() - started
            self._stats.record_pipeline_completed(elapsed)
            self._stats.record_request_completed()
            self._stats.record_snapshot_published()

            response = self._factory.create_success_response(
                request,
                snapshot  = snapshot,
                elapsed_s = elapsed,
            )
            self._history.record_response(response)
            self._registry.register_response(response)
            return response

        except Exception as exc:  # noqa: BLE001
            elapsed = time.time() - started
            _log.warning(
                f"Risk workflow failed for {request.risk_id}/{request.portfolio_id}: {exc}"
            )
            self._stats.record_pipeline_failed()
            self._stats.record_request_failed()

            if session is not None:
                try:
                    self._session_manager.fail_session(session, error=str(exc))
                    self._stats.record_session_failed()
                except Exception:  # noqa: BLE001
                    pass

            pipeline.fail(str(exc))
            self._registry.archive_pipeline(pipeline)
            self._history.record_pipeline(pipeline)

            ev = make_risk_failed(
                request.risk_id,
                request.portfolio_id,
                session.session_id if session else "",
                pipeline_id = pipeline.pipeline_id,
                payload     = {"error": str(exc)},
            )
            self._history.record_event(ev)
            self._dispatch_ev(ev)

            response = self._factory.create_failure_response(
                request,
                error_message = str(exc),
                elapsed_s     = elapsed,
            )
            self._history.record_response(response)
            self._registry.register_response(response)
            return response

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------

    def _phase_initialize(
        self,
        pipeline: RiskPipeline,
        request:  RiskRequest,
    ):  # returns RiskSession
        stage_start = time.time()
        from iios.risk.lifecycle import RiskType, RiskScope

        wtype = request.workflow_type
        risk_type = RiskType.CUSTOM
        if wtype.value in ("position_risk_assessment",):
            risk_type = RiskType.MARKET
        elif wtype.value in ("account_risk_assessment",):
            risk_type = RiskType.CREDIT
        elif wtype.value in ("stress_test", "scenario_analysis"):
            risk_type = RiskType.TAIL

        session = self._session_manager.create_session(
            risk_id      = request.risk_id,
            portfolio_id = request.portfolio_id,
            risk_type    = risk_type,
        )
        pipeline.session_id = session.session_id
        self._stats.record_session_created()

        session = self._session_manager.initialize_session(session)

        pipeline.add_stage(PipelineStage(
            stage_name   = "initialize",
            engine_state = EngineState.INITIALIZING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

        ev = make_risk_initialized(
            request.risk_id,
            request.portfolio_id,
            session.session_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)

        return session

    def _phase_collect(
        self,
        pipeline: RiskPipeline,
        request:  RiskRequest,
        session,
    ):  # returns updated RiskSession
        stage_start = time.time()
        session = self._session_manager.collect_session(session)

        pipeline.add_stage(PipelineStage(
            stage_name   = "collect",
            engine_state = EngineState.COLLECTING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

        ev = make_risk_collected(
            request.risk_id,
            request.portfolio_id,
            session.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)
        return session

    def _phase_validate(
        self,
        pipeline: RiskPipeline,
        request:  RiskRequest,
        session,
    ):  # returns updated RiskSession (READY)
        stage_start = time.time()
        # Engine-level validation
        result = self._validator.validate_request(request)
        if not result.is_valid:
            pipeline.add_stage(PipelineStage(
                stage_name   = "validate",
                engine_state = EngineState.VALIDATING,
                status       = PipelineStatus.FAILED,
                started_at   = stage_start,
                completed_at = time.time(),
                error        = "; ".join(result.error_messages),
            ))
            raise RiskEngineValidationError(
                "; ".join(result.error_messages),
                failed_checks = tuple(result.failed_checks),
            )

        # Drive lifecycle: COLLECTING → VALIDATING → READY
        session = self._session_manager.validate_session(session)
        session = self._session_manager.ready_session(session)

        pipeline.add_stage(PipelineStage(
            stage_name   = "validate",
            engine_state = EngineState.VALIDATING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))
        return session

    def _phase_dispatch(
        self,
        pipeline: RiskPipeline,
        request:  RiskRequest,
    ) -> EngineState:
        stage_start = time.time()
        dispatch_started = time.time()
        self._dispatcher.dispatch(pipeline, request)
        dispatch_elapsed = time.time() - dispatch_started
        self._stats.record_dispatch_time(dispatch_elapsed)

        pipeline.add_stage(PipelineStage(
            stage_name   = "dispatch",
            engine_state = EngineState.DISPATCHING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

        ev = make_risk_dispatched(
            request.risk_id,
            request.portfolio_id,
            pipeline.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)

        return self._dispatcher.determine_next_state(request.workflow_type)

    def _phase_assess_or_monitor(
        self,
        pipeline:   RiskPipeline,
        request:    RiskRequest,
        session,
        next_state: EngineState,
    ):  # returns updated RiskSession
        assess_start = time.time()

        # Always drive through ASSESSING (required by lifecycle)
        session = self._session_manager.start_assessment_session(session)

        ev = make_risk_assessment_started(
            request.risk_id,
            request.portfolio_id,
            session.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)

        if next_state in (EngineState.ASSESSING, EngineState.MONITORING):
            # For monitoring workflows also advance to MONITORING
            monitor_start = time.time()
            try:
                session = self._session_manager.start_monitoring_session(session)
                pipeline.add_stage(PipelineStage(
                    stage_name   = "monitor",
                    engine_state = EngineState.MONITORING,
                    status       = PipelineStatus.COMPLETED,
                    started_at   = monitor_start,
                    completed_at = time.time(),
                ))
            except Exception:  # noqa: BLE001
                # MONITORING is optional — record ASSESSING stage only
                pipeline.add_stage(PipelineStage(
                    stage_name   = "assess",
                    engine_state = EngineState.ASSESSING,
                    status       = PipelineStatus.COMPLETED,
                    started_at   = assess_start,
                    completed_at = time.time(),
                ))
        else:
            # PUBLISHING path — ASSESSING only
            pipeline.add_stage(PipelineStage(
                stage_name   = "assess",
                engine_state = EngineState.ASSESSING,
                status       = PipelineStatus.COMPLETED,
                started_at   = assess_start,
                completed_at = time.time(),
            ))

        return session

    def _phase_publish(
        self,
        pipeline: RiskPipeline,
        request:  RiskRequest,
        session,
    ) -> RiskEngineSnapshot:
        stage_start = time.time()

        snapshot = self._factory.create_snapshot(
            request.risk_id,
            request.portfolio_id,
            session.session_id,
            request.workflow_type,
            EngineState.PUBLISHING,
            inputs_summary = {k: type(v).__name__ for k, v in request.inputs.items()},
            outputs        = {},
        )

        pipeline.add_stage(PipelineStage(
            stage_name   = "publish",
            engine_state = EngineState.PUBLISHING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

        ev = make_risk_published(
            request.risk_id,
            request.portfolio_id,
            session.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)

        return snapshot

    def _phase_complete(
        self,
        pipeline: RiskPipeline,
        request:  RiskRequest,
        session,
    ) -> None:
        completed_session = self._session_manager.complete_session(session)
        self._stats.record_session_completed()

        pipeline.complete()
        self._registry.archive_pipeline(pipeline)
        self._history.record_pipeline(pipeline)

        ev = make_risk_completed(
            request.risk_id,
            request.portfolio_id,
            completed_session.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)
