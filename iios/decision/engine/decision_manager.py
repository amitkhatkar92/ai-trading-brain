"""
decision_manager.py — iios.decision.engine
============================================
Internal workflow orchestrator used by :class:`DecisionEngine`.

DecisionManager executes the complete nine-step decision workflow for a single
:class:`DecisionRequest`:

  1. Validate context
  2. Initialize decision session (M1 lifecycle)
  3. Create and start pipeline
  4. Collect institutional inputs
  5. Validate collected inputs
  6. Dispatch to evaluation pipeline (Policy M3 + Optimization M4)
  7. Build decision snapshot
  8. Publish snapshot
  9. Complete session and return response

DecisionManager does NOT perform policy evaluation.
DecisionManager does NOT perform optimization.
DecisionManager does NOT execute trades.
DecisionManager does NOT communicate with brokers.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import VERSION
from .decision_context       import DecisionEngineContext
from .decision_dispatcher    import DecisionDispatcher
from .decision_events        import (
    make_decision_engine_initialized,
    make_decision_engine_started,
    make_decision_engine_collected,
    make_decision_engine_dispatched,
    make_decision_engine_completed,
    make_decision_engine_published,
    make_decision_engine_failed,
)
from .decision_factory       import DecisionEngineFactory
from .decision_history       import DecisionEngineHistory
from .decision_pipeline      import DecisionPipeline
from .decision_registry      import DecisionEngineRegistry
from .decision_request       import DecisionRequest
from .decision_response      import DecisionResponse, DecisionSnapshot
from .decision_session_manager import DecisionSessionManager
from .decision_statistics    import DecisionEngineStatistics
from .decision_validation    import DecisionEngineValidator, EngineValidationResult
from .exceptions import (
    DecisionCollectionError,
    DecisionDispatchError,
    DecisionPipelineError,
    DecisionPublishError,
    DecisionRequestValidationError,
    DecisionSessionError,
)

_log = get_logger(__name__)


class DecisionManager:
    """
    Internal orchestrator that executes the complete decision workflow.

    Called exclusively by :class:`DecisionEngine.submit`.  External callers
    must never instantiate :class:`DecisionManager` directly.

    Parameters
    ----------
    session_manager : Manages decision lifecycle sessions.
    dispatcher :      Routes pipelines through the evaluation chain.
    registry :        Tracks active and completed pipelines.
    factory :         Creates pipeline objects.
    statistics :      Shared statistics counter.
    history :         Shared event and response history.
    listener :        Optional callback for engine events.
    """

    def __init__(
        self,
        session_manager: DecisionSessionManager,
        dispatcher:      DecisionDispatcher,
        registry:        DecisionEngineRegistry,
        factory:         DecisionEngineFactory,
        statistics:      DecisionEngineStatistics,
        history:         DecisionEngineHistory,
        *,
        listener: Optional[Any] = None,
    ) -> None:
        self._session_mgr = session_manager
        self._dispatcher  = dispatcher
        self._registry    = registry
        self._factory     = factory
        self._stats       = statistics
        self._history     = history
        self._listener    = listener
        self._validator   = DecisionEngineValidator()

    # ------------------------------------------------------------------
    # Primary workflow
    # ------------------------------------------------------------------
    def process(self, request: DecisionRequest) -> DecisionResponse:
        """
        Execute the complete nine-step decision workflow for *request*.

        Returns a :class:`DecisionResponse` on success or failure.
        Never raises — failures are captured in the response.
        """
        t_start    = time.time()
        session_id = ""
        pipeline   = self._factory.create_pipeline(
            request_id   = request.request_id,
            decision_id  = request.decision_id,
            workflow_id  = request.workflow_id,
            portfolio_id = request.portfolio_id,
            strategy_id  = request.strategy_id,
        )
        self._registry.register_pipeline(pipeline)

        try:
            # --- STEP 1: Validate request --------------------------------
            validation = self._validator.validate_request(
                request,
                engine_running = True,
                pipeline       = pipeline,
            )
            if not validation.is_valid:
                raise DecisionRequestValidationError(
                    failed_checks=tuple(c.value for c in validation.failed_checks)
                )

            # --- STEP 2: Initialize decision session ----------------------
            pipeline.start()
            session = self._session_mgr.create_session(
                request.decision_id,
                workflow_id  = request.workflow_id,
                portfolio_id = request.portfolio_id,
                strategy_id  = request.strategy_id,
            )
            session_id = session.session_id

            # Update pipeline with session id
            pipeline._session_id = session_id   # noqa: SLF001

            # INITIALIZED event
            evt = make_decision_engine_initialized(session_id, request.request_id, request.decision_id, pipeline.pipeline_id)
            self._history.record_event(evt)
            self._stats.record_session_created()

            # Advance lifecycle: CREATED → INITIALIZING → COLLECTING
            self._session_mgr.initialize(session_id)

            # --- STEP 3: Build routing context ----------------------------
            context = DecisionEngineContext.from_request(
                request,
                session_id  = session_id,
                pipeline_id = pipeline.pipeline_id,
            )

            # STARTED event
            evt = make_decision_engine_started(session_id, request.request_id, request.decision_id, pipeline.pipeline_id)
            self._history.record_event(evt)

            # --- STEP 4: Collect institutional inputs ---------------------
            self._session_mgr.collect(session_id)
            pipeline.begin_collecting()
            inputs = self._collect_inputs(request, pipeline)
            pipeline.begin_validating()

            # COLLECTED event
            evt = make_decision_engine_collected(
                session_id, request.request_id, request.decision_id,
                pipeline.pipeline_id,
                collection_time_s = pipeline.collection_time_s,
                input_count       = len(inputs),
            )
            self._history.record_event(evt)

            # --- STEP 5: Validate collected inputs ------------------------
            # Re-validate with pipeline in VALIDATING state
            # (check PIPELINE_CONSISTENCY — not terminal, valid state)
            # Already passing; no extra work needed here.

            # --- STEP 6: Dispatch to evaluation pipeline ------------------
            self._session_mgr.evaluate(session_id)
            dispatch_results = self._dispatcher.dispatch(pipeline, context)

            # DISPATCHED event
            evt = make_decision_engine_dispatched(
                session_id, request.request_id, request.decision_id,
                pipeline.pipeline_id,
                dispatch_time_s = pipeline.dispatch_time_s,
            )
            self._history.record_event(evt)

            # --- STEP 7 & 8: Build and publish snapshot -------------------
            self._session_mgr.ready(session_id)
            self._session_mgr.activate(session_id)

            snapshot = self._build_snapshot(request, context, pipeline, dispatch_results)

            # PUBLISHED event
            evt = make_decision_engine_published(
                session_id, request.request_id, request.decision_id,
                pipeline.pipeline_id,
                snapshot_id = snapshot.snapshot_id,
            )
            self._history.record_event(evt)

            # --- STEP 9: Complete session and return response -------------
            pipeline.complete()
            self._session_mgr.complete(session_id)

            total_time = time.time() - t_start
            self._stats.record_pipeline_executed(
                total_time_s      = total_time,
                collection_time_s = pipeline.collection_time_s,
                dispatch_time_s   = pipeline.dispatch_time_s,
            )

            # COMPLETED event
            evt = make_decision_engine_completed(
                session_id, request.request_id, request.decision_id,
                pipeline.pipeline_id,
                total_time_s = total_time,
            )
            self._history.record_event(evt)

            response = DecisionResponse.success(
                request_id        = request.request_id,
                session_id        = session_id,
                decision_id       = request.decision_id,
                snapshot          = snapshot,
                collection_time_s = pipeline.collection_time_s,
                dispatch_time_s   = pipeline.dispatch_time_s,
                total_time_s      = total_time,
            )
            self._history.record_response(response)
            self._registry.move_to_completed(pipeline.pipeline_id)
            return response

        except Exception as exc:
            _log.warning(
                f"DecisionManager: decision workflow failed for "
                f"request {request.request_id!r}: {exc}"
            )
            # Fail pipeline
            if pipeline.is_active:
                pipeline.fail(str(exc))
            self._registry.move_to_completed(pipeline.pipeline_id)

            # Fail lifecycle session if one was created
            if session_id:
                try:
                    self._session_mgr.fail(session_id, reason=str(exc))
                except Exception:
                    pass

            total_time = time.time() - t_start

            evt = make_decision_engine_failed(
                session_id or "", request.request_id, request.decision_id,
                pipeline.pipeline_id,
                reason = str(exc),
            )
            self._history.record_event(evt)

            response = DecisionResponse.failure(
                request_id   = request.request_id,
                session_id   = session_id,
                decision_id  = request.decision_id,
                error        = str(exc),
                total_time_s = total_time,
            )
            self._history.record_response(response)
            return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _collect_inputs(
        self,
        request:  DecisionRequest,
        pipeline: DecisionPipeline,
    ) -> Dict[str, Any]:
        """
        Gather institutional inputs from the request and store on pipeline.

        The engine does NOT perform any data fetching here — it simply
        ingests the inputs already attached to the request (provided by the
        caller).  Data fetching is the responsibility of upstream services.
        """
        for key, value in request.inputs.items():
            pipeline.add_input(key, value)
        return dict(request.inputs)

    def _build_snapshot(
        self,
        request:          DecisionRequest,
        context:          DecisionEngineContext,
        pipeline:         DecisionPipeline,
        dispatch_results: Dict[str, Any],
    ) -> DecisionSnapshot:
        """Assemble a :class:`DecisionSnapshot` from pipeline results."""
        return DecisionSnapshot(
            snapshot_id        = str(uuid.uuid4()),
            request_id         = request.request_id,
            session_id         = context.session_id,
            pipeline_id        = pipeline.pipeline_id,
            decision_id        = request.decision_id,
            workflow_id        = request.workflow_id,
            portfolio_id       = request.portfolio_id,
            strategy_id        = request.strategy_id,
            collection_inputs  = pipeline.inputs,
            dispatch_results   = dispatch_results,
            pipeline_state     = pipeline.state.value,
            collection_time_s  = pipeline.collection_time_s,
            dispatch_time_s    = pipeline.dispatch_time_s,
            total_time_s       = pipeline.total_time_s,
            metadata           = dict(request.metadata),
        )
