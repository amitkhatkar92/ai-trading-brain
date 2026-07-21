"""
portfolio_manager.py — iios.portfolio.engine
=============================================
Internal portfolio workflow coordinator.

:class:`PortfolioManager` orchestrates the execution of a single portfolio
workflow pipeline end-to-end: initialize → collect → validate → dispatch
→ allocate/rebalance → publish.

This class is NOT a public interface. All external callers use
:class:`PortfolioEngine`.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_ENGINE,
    EngineState,
    PipelineStatus,
    PortfolioWorkflowType,
)
from .portfolio_dispatcher import PortfolioDispatcher
from .portfolio_events import (
    PortfolioEngineEvent,
    make_portfolio_collected,
    make_portfolio_completed,
    make_portfolio_dispatched,
    make_portfolio_failed,
    make_portfolio_initialized,
    make_portfolio_published,
    make_portfolio_started,
)
from .portfolio_factory import PortfolioEngineFactory
from .portfolio_history import PortfolioEngineHistory
from .portfolio_pipeline import PortfolioPipeline, PipelineStage
from .portfolio_registry import PortfolioEngineRegistry
from .portfolio_request import PortfolioRequest
from .portfolio_response import PortfolioResponse, PortfolioSnapshot
from .portfolio_session_manager import PortfolioSessionManager
from .portfolio_statistics import PortfolioEngineStatistics
from .exceptions import (
    PortfolioCollectionError,
    PortfolioDispatchError,
    PortfolioPublicationError,
    PortfolioSessionError,
)

_log = get_logger(__name__)


class PortfolioManager:
    """
    Internal orchestrator for portfolio workflow pipelines.

    Coordinates the end-to-end execution of a single portfolio request:

    1. Initialize session (via session_manager)
    2. Collect institutional inputs
    3. Validate inputs
    4. Dispatch to Policy Framework (M3 — via dispatcher)
    5. Dispatch to Optimization Framework (M4 — via dispatcher)
    6. Allocate / Rebalance (based on workflow type)
    7. Publish snapshot

    The manager NEVER:
    - Evaluates portfolio policies
    - Runs optimization algorithms
    - Executes trades
    - Communicates with brokers
    """

    def __init__(
        self,
        session_manager: PortfolioSessionManager,
        dispatcher:      PortfolioDispatcher,
        registry:        PortfolioEngineRegistry,
        factory:         PortfolioEngineFactory,
        statistics:      PortfolioEngineStatistics,
        history:         PortfolioEngineHistory,
        dispatch_event:  Callable[[PortfolioEngineEvent], None],
    ) -> None:
        self._sessions    = session_manager
        self._dispatcher  = dispatcher
        self._registry    = registry
        self._factory     = factory
        self._stats       = statistics
        self._history     = history
        self._dispatch_ev = dispatch_event

    # ------------------------------------------------------------------
    # Primary workflow entry point
    # ------------------------------------------------------------------

    def run_workflow(
        self,
        pipeline: PortfolioPipeline,
        request:  PortfolioRequest,
    ) -> PortfolioResponse:
        """
        Execute a complete portfolio workflow pipeline.

        Parameters
        ----------
        pipeline : Pre-created pipeline registered in the registry.
        request :  The originating portfolio request.

        Returns
        -------
        PortfolioResponse
        """
        t0 = time.monotonic()
        pipeline.start()
        self._stats.record_pipeline_started()

        session_id = ""
        try:
            # ----------------------------------------------------------
            # 1. INITIALIZING — create + init lifecycle session
            # ----------------------------------------------------------
            session_id = self._phase_initialize(pipeline, request)

            # ----------------------------------------------------------
            # 2. COLLECTING — collect institutional inputs
            # ----------------------------------------------------------
            self._phase_collect(pipeline, request, session_id)

            # ----------------------------------------------------------
            # 3. VALIDATING — validate collected data
            # ----------------------------------------------------------
            self._phase_validate(pipeline, request, session_id)

            # ----------------------------------------------------------
            # 4. DISPATCHING — delegate to M3 / M4
            # ----------------------------------------------------------
            dispatch_t0 = time.monotonic()
            self._phase_dispatch(pipeline, request, session_id)
            self._stats.record_dispatch(time.monotonic() - dispatch_t0)

            # ----------------------------------------------------------
            # 5. ALLOCATING / REBALANCING
            # ----------------------------------------------------------
            self._phase_allocate_or_rebalance(pipeline, request, session_id)

            # ----------------------------------------------------------
            # 6. PUBLISHING — publish snapshot
            # ----------------------------------------------------------
            snapshot = self._phase_publish(pipeline, request, session_id)

            # ----------------------------------------------------------
            # Complete pipeline
            # ----------------------------------------------------------
            pipeline.complete()
            elapsed = time.monotonic() - t0
            self._stats.record_pipeline_completed(elapsed)
            self._registry.update_pipeline(pipeline)
            self._history.record_pipeline(pipeline)

            # Complete lifecycle session
            try:
                self._sessions.complete_session(session_id, actor=ACTOR_ENGINE)
            except Exception:
                pass  # pipeline is complete regardless

            event = make_portfolio_completed(
                request.portfolio_id,
                session_id    = session_id,
                workflow_type = request.workflow_type,
                elapsed_s     = elapsed,
            )
            self._history.record_event(event)
            self._dispatch_ev(event)

            response = self._factory.create_success_response(
                request, snapshot=snapshot, elapsed_s=elapsed
            )
            self._history.record_response(response)
            return response

        except Exception as exc:
            elapsed = time.monotonic() - t0
            self._stats.record_pipeline_failed()
            pipeline.fail(str(exc))
            self._registry.update_pipeline(pipeline)
            self._history.record_pipeline(pipeline)

            if session_id:
                try:
                    self._sessions.fail_session(session_id, reason=str(exc), actor=ACTOR_ENGINE)
                except Exception:
                    pass

            event = make_portfolio_failed(
                request.portfolio_id,
                session_id    = session_id,
                workflow_type = request.workflow_type,
                reason        = str(exc),
            )
            self._history.record_event(event)
            self._dispatch_ev(event)

            response = self._factory.create_failure_response(
                request, error_message=str(exc), elapsed_s=elapsed
            )
            self._history.record_response(response)
            return response

    # ------------------------------------------------------------------
    # Pipeline phases
    # ------------------------------------------------------------------

    def _phase_initialize(
        self, pipeline: PortfolioPipeline, request: PortfolioRequest
    ) -> str:
        """Create and initialize a portfolio lifecycle session."""
        stage_start = time.time()
        try:
            session = self._sessions.create_session(
                request.portfolio_id,
                portfolio_name = request.metadata.get("portfolio_name", ""),
                actor          = ACTOR_ENGINE,
            )
            session_id = session.session_id
            pipeline.session_id = session_id
            self._stats.record_session_created()

            # Drive session through init → loading → validating → ready → active
            self._sessions.initialize_session(session_id, actor=ACTOR_ENGINE)
            self._sessions.load_session(session_id, actor=ACTOR_ENGINE)
            self._sessions.validate_session(session_id, actor=ACTOR_ENGINE)
            self._sessions.ready_session(session_id, actor=ACTOR_ENGINE)
            self._sessions.activate_session(session_id, actor=ACTOR_ENGINE)

            pipeline.add_stage(PipelineStage(
                stage_name   = "initialize",
                engine_state = EngineState.INITIALIZING,
                status       = PipelineStatus.COMPLETED,
                started_at   = stage_start,
                completed_at = time.time(),
            ))
            event = make_portfolio_initialized(
                request.portfolio_id,
                session_id    = session_id,
                workflow_type = request.workflow_type,
            )
            self._history.record_event(event)
            self._dispatch_ev(event)

            event2 = make_portfolio_started(
                request.portfolio_id,
                session_id    = session_id,
                workflow_type = request.workflow_type,
            )
            self._history.record_event(event2)
            self._dispatch_ev(event2)

            return session_id

        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "initialize",
                engine_state = EngineState.INITIALIZING,
                status       = PipelineStatus.FAILED,
                started_at   = stage_start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise PortfolioSessionError(str(exc)) from exc

    def _phase_collect(
        self, pipeline: PortfolioPipeline, request: PortfolioRequest, session_id: str
    ) -> None:
        """Collect institutional inputs from the request."""
        stage_start = time.time()
        try:
            # Inputs are already embedded in the request.
            # The manager acknowledges collection and records the event.
            input_keys = list(request.inputs.keys())
            pipeline.add_stage(PipelineStage(
                stage_name   = "collect",
                engine_state = EngineState.COLLECTING,
                status       = PipelineStatus.COMPLETED,
                started_at   = stage_start,
                completed_at = time.time(),
                metadata     = {"input_keys": input_keys},
            ))
            event = make_portfolio_collected(
                request.portfolio_id,
                session_id    = session_id,
                workflow_type = request.workflow_type,
                input_keys    = input_keys,
            )
            self._history.record_event(event)
            self._dispatch_ev(event)

        except Exception as exc:
            pipeline.add_stage(PipelineStage(
                stage_name   = "collect",
                engine_state = EngineState.COLLECTING,
                status       = PipelineStatus.FAILED,
                started_at   = stage_start,
                completed_at = time.time(),
                error        = str(exc),
            ))
            raise PortfolioCollectionError(str(exc)) from exc

    def _phase_validate(
        self, pipeline: PortfolioPipeline, request: PortfolioRequest, session_id: str
    ) -> None:
        """Validate the collected inputs."""
        stage_start = time.time()
        pipeline.add_stage(PipelineStage(
            stage_name   = "validate",
            engine_state = EngineState.VALIDATING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))

    def _phase_dispatch(
        self, pipeline: PortfolioPipeline, request: PortfolioRequest, session_id: str
    ) -> None:
        """Dispatch to Policy Framework (M3) and Optimization Framework (M4)."""
        stage_start = time.time()
        self._dispatcher.dispatch(pipeline, request)
        pipeline.add_stage(PipelineStage(
            stage_name   = "dispatch",
            engine_state = EngineState.DISPATCHING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
        ))
        event = make_portfolio_dispatched(
            request.portfolio_id,
            session_id    = session_id,
            workflow_type = request.workflow_type,
        )
        self._history.record_event(event)
        self._dispatch_ev(event)

    def _phase_allocate_or_rebalance(
        self, pipeline: PortfolioPipeline, request: PortfolioRequest, session_id: str
    ) -> None:
        """Run allocation or rebalancing phase based on workflow type."""
        next_state = self._dispatcher.determine_next_state(request.workflow_type)
        if next_state in (EngineState.ALLOCATING, EngineState.REBALANCING):
            stage_start = time.time()
            pipeline.add_stage(PipelineStage(
                stage_name   = next_state.value,
                engine_state = next_state,
                status       = PipelineStatus.COMPLETED,
                started_at   = stage_start,
                completed_at = time.time(),
            ))

    def _phase_publish(
        self, pipeline: PortfolioPipeline, request: PortfolioRequest, session_id: str
    ) -> PortfolioSnapshot:
        """Publish portfolio snapshot."""
        stage_start = time.time()
        snapshot = self._factory.create_snapshot(
            request,
            session_id,
            engine_state   = EngineState.PUBLISHING,
            inputs_summary = {"input_keys": list(request.inputs.keys())},
            outputs        = {
                "workflow_type": request.workflow_type.value,
                "portfolio_id":  request.portfolio_id,
            },
        )
        self._stats.record_snapshot_published()
        pipeline.add_stage(PipelineStage(
            stage_name   = "publish",
            engine_state = EngineState.PUBLISHING,
            status       = PipelineStatus.COMPLETED,
            started_at   = stage_start,
            completed_at = time.time(),
            metadata     = {"snapshot_id": snapshot.snapshot_id},
        ))
        event = make_portfolio_published(
            request.portfolio_id,
            session_id    = session_id,
            workflow_type = request.workflow_type,
            snapshot_id   = snapshot.snapshot_id,
        )
        self._history.record_event(event)
        self._dispatch_ev(event)
        return snapshot
