"""
market_manager.py — iios.market.engine
=========================================
Internal workflow coordinator for the Market Engine.

**NOT a public interface.**  Only ``MarketEngine`` may call this class.

Drives a single market pipeline through seven sequential phases:
  1. Initialize
  2. Collect
  3. Validate (structural)
  4. Dispatch
  5. Analyze or Monitor (routing determined by workflow type)
  6. Publish
  7. Complete

Each phase records a :class:`~.market_pipeline.PipelineStage` on the
pipeline and emits a :class:`~.market_events.MarketEngineEvent` into history.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    EngineState,
    PipelineStatus,
    ANALYSIS_WORKFLOWS,
    MONITORING_WORKFLOWS,
)
from .market_context import MarketEngineContext
from .market_events import (
    make_market_engine_initialized,
    make_market_engine_started,
    make_market_engine_collected,
    make_market_engine_dispatched,
    make_market_engine_analysis_started,
    make_market_engine_published,
    make_market_engine_completed,
    make_market_engine_failed,
)
from .market_factory import MarketEngineFactory
from .market_history import MarketEngineHistory
from .market_pipeline import MarketPipeline, PipelineStage
from .market_registry import MarketEngineRegistry
from .market_request import MarketRequest
from .market_response import MarketEngineSnapshot, MarketResponse
from .market_dispatcher import MarketDispatcher
from .market_session_manager import MarketSessionManager
from .market_statistics import MarketEngineStatistics
from .market_validation import MarketEngineValidator
from .exceptions import (
    MarketEngineValidationError,
    MarketSessionError,
    MarketCollectionError,
    MarketDispatchError,
)

_log = get_logger(__name__)


class MarketManager:
    """
    Internal workflow coordinator.

    Parameters
    ----------
    session_manager : MarketSessionManager wrapping M1 lifecycle.
    dispatcher :      MarketDispatcher holding M3/M4 hooks.
    registry :        MarketEngineRegistry.
    factory :         MarketEngineFactory.
    validator :       MarketEngineValidator.
    statistics :      MarketEngineStatistics.
    history :         MarketEngineHistory.
    listener_fn :     Callable to dispatch events to external listeners.
    """

    def __init__(
        self,
        session_manager: MarketSessionManager,
        dispatcher:      MarketDispatcher,
        registry:        MarketEngineRegistry,
        factory:         MarketEngineFactory,
        validator:       MarketEngineValidator,
        statistics:      MarketEngineStatistics,
        history:         MarketEngineHistory,
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
        pipeline: MarketPipeline,
        request:  MarketRequest,
    ) -> MarketResponse:
        """
        Execute all seven workflow phases and return the response.

        Never raises — all failures are caught and returned as a failure
        :class:`MarketResponse`.
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

            # ── Phase 5: Analyze or Monitor ───────────────────────────
            session = self._phase_analyze_or_monitor(
                pipeline, request, session, next_state
            )

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

        except Exception as exc:    # noqa: BLE001
            elapsed = time.time() - started
            _log.warning(
                f"Market workflow failed for "
                f"{request.market_analysis_id}/{request.exchange}: {exc}"
            )
            self._stats.record_pipeline_failed()
            self._stats.record_request_failed()

            if session is not None:
                try:
                    self._session_manager.fail_session(session, error=str(exc))
                    self._stats.record_session_failed()
                except Exception:   # noqa: BLE001
                    pass

            pipeline.fail(str(exc))
            self._registry.archive_pipeline(pipeline)
            self._history.record_pipeline(pipeline)

            ev = make_market_engine_failed(
                request.market_analysis_id,
                request.exchange,
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
        pipeline: MarketPipeline,
        request:  MarketRequest,
    ):  # returns MarketSession
        from iios.market.lifecycle import MarketType, MarketScope

        stage_start = time.time()

        wtype = request.workflow_type
        market_type = MarketType.EQUITY
        if wtype.value in ("index_analysis", "breadth_review"):
            market_type = MarketType.INDEX
        elif wtype.value in ("volatility_monitoring",):
            market_type = MarketType.OPTIONS

        session = self._session_manager.create_session(
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            market_type        = market_type,
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

        ev = make_market_engine_initialized(
            request.market_analysis_id,
            request.exchange,
            session.session_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)

        return session

    def _phase_collect(
        self,
        pipeline: MarketPipeline,
        request:  MarketRequest,
        session,
    ):  # returns updated MarketSession
        stage_start = time.time()
        session = self._session_manager.collect_session(session)

        pipeline.add_stage(PipelineStage(
            stage_name   = "collect",
            engine_state = EngineState.COLLECTING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

        ev = make_market_engine_collected(
            request.market_analysis_id,
            request.exchange,
            session.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)
        return session

    def _phase_validate(
        self,
        pipeline: MarketPipeline,
        request:  MarketRequest,
        session,
    ):  # returns updated MarketSession (READY)
        stage_start = time.time()
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
            raise MarketEngineValidationError(
                "; ".join(result.error_messages),
                failed_checks=tuple(result.failed_checks),
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
        pipeline: MarketPipeline,
        request:  MarketRequest,
    ) -> EngineState:
        stage_start = time.time()
        dispatch_start = time.time()
        self._dispatcher.dispatch(pipeline, request)
        dispatch_elapsed = time.time() - dispatch_start
        self._stats.record_dispatch_time(dispatch_elapsed)

        pipeline.add_stage(PipelineStage(
            stage_name   = "dispatch",
            engine_state = EngineState.DISPATCHING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

        ev = make_market_engine_dispatched(
            request.market_analysis_id,
            request.exchange,
            pipeline.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)

        return self._dispatcher.determine_next_state(request.workflow_type)

    def _phase_analyze_or_monitor(
        self,
        pipeline:   MarketPipeline,
        request:    MarketRequest,
        session,
        next_state: EngineState,
    ):  # returns updated MarketSession
        stage_start = time.time()

        if next_state == EngineState.ANALYZING:
            session = self._session_manager.start_analysis_session(session)
            pipeline.add_stage(PipelineStage(
                stage_name   = "analyze",
                engine_state = EngineState.ANALYZING,
                status       = PipelineStatus.COMPLETED,
                started_at   = stage_start,
                completed_at = time.time(),
            ))
            ev = make_market_engine_analysis_started(
                request.market_analysis_id,
                request.exchange,
                session.session_id,
                pipeline_id = pipeline.pipeline_id,
            )
            self._history.record_event(ev)
            self._dispatch_ev(ev)

        elif next_state == EngineState.MONITORING:
            session = self._session_manager.start_analysis_session(session)
            session = self._session_manager.start_monitoring_session(session)
            pipeline.add_stage(PipelineStage(
                stage_name   = "monitor",
                engine_state = EngineState.MONITORING,
                status       = PipelineStatus.COMPLETED,
                started_at   = stage_start,
                completed_at = time.time(),
            ))
        else:
            # PUBLISHING — skip analysis/monitoring for this workflow
            pass

        return session

    def _phase_publish(
        self,
        pipeline: MarketPipeline,
        request:  MarketRequest,
        session,
    ) -> MarketEngineSnapshot:
        stage_start = time.time()

        snapshot = self._factory.create_snapshot(
            request.market_analysis_id,
            request.exchange,
            session.session_id,
            request.workflow_type,
            EngineState.PUBLISHING,
            inputs_summary = {k: True for k in request.inputs.keys()},
            outputs        = {},
        )

        pipeline.add_stage(PipelineStage(
            stage_name   = "publish",
            engine_state = EngineState.PUBLISHING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

        ev = make_market_engine_published(
            request.market_analysis_id,
            request.exchange,
            session.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)

        return snapshot

    def _phase_complete(
        self,
        pipeline: MarketPipeline,
        request:  MarketRequest,
        session,
    ) -> None:
        stage_start = time.time()

        self._session_manager.complete_session(session)
        self._stats.record_session_completed()

        pipeline.complete()
        self._registry.archive_pipeline(pipeline)
        self._history.record_pipeline(pipeline)

        pipeline.add_stage(PipelineStage(
            stage_name   = "complete",
            engine_state = EngineState.COMPLETED,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

        ev = make_market_engine_completed(
            request.market_analysis_id,
            request.exchange,
            session.session_id,
            pipeline_id = pipeline.pipeline_id,
        )
        self._history.record_event(ev)
        self._dispatch_ev(ev)
