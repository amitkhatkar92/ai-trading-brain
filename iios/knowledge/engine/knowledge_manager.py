"""
knowledge_manager.py — iios.knowledge.engine
----------------------------------------------
Internal knowledge workflow coordinator.

THIS IS AN INTERNAL MODULE — NOT PART OF THE PUBLIC API.

Orchestrates the 10-phase knowledge workflow pipeline:
  1. Validate Context       — validate the incoming request
  2. Initialize Session     — create and initialize a lifecycle session
  3. Start Collection       — enter COLLECTING state
  4. Collect Artifacts      — gather enterprise knowledge
  5. Validate Artifacts     — structural validation of collected data
  6. Classify               — classify knowledge by type and scope
  7. Dispatch               — route to M3 (Governance) and M4 (Intelligence)
  8. Build Snapshot         — construct the knowledge snapshot
  9. Publish                — mark session as published
 10. Complete               — finalize session and pipeline

NEVER RAISES.  All exceptions are caught and returned as failure responses.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_ENGINE,
    ENGINE_SYSTEM_ID,
    EngineState,
    KnowledgeWorkflowType,
    PipelineStatus,
)
from .knowledge_dispatcher import KnowledgeDispatcher
from .knowledge_events import (
    KnowledgeEngineEvent,
    make_knowledge_initialized,
    make_knowledge_collection_started,
    make_knowledge_collected,
    make_knowledge_validated,
    make_knowledge_classified,
    make_knowledge_dispatched,
    make_knowledge_published,
    make_knowledge_completed,
    make_knowledge_failed,
)
from .knowledge_factory import KnowledgeEngineFactory
from .knowledge_history import KnowledgeEngineHistory
from .knowledge_pipeline import KnowledgePipeline, PipelineStage
from .knowledge_registry import KnowledgeEngineRegistry
from .knowledge_request import KnowledgeRequest
from .knowledge_response import KnowledgeResponse
from .knowledge_session_manager import KnowledgeSessionManager
from .knowledge_statistics import KnowledgeEngineStatistics
from .knowledge_validation import KnowledgeEngineValidator

_log = get_logger(ENGINE_SYSTEM_ID)


class KnowledgeWorkflowManager:
    """
    Runs a complete knowledge workflow pipeline.

    Injected with collaborator components from the engine.  All phases are
    invoked sequentially; a failed phase immediately short-circuits to
    ``_build_failure_response``.
    """

    def __init__(
        self,
        session_manager: KnowledgeSessionManager,
        dispatcher:      KnowledgeDispatcher,
        factory:         KnowledgeEngineFactory,
        validator:       KnowledgeEngineValidator,
        statistics:      KnowledgeEngineStatistics,
        history:         KnowledgeEngineHistory,
        registry:        KnowledgeEngineRegistry,
        event_listeners: List[Callable],
    ) -> None:
        self._sm        = session_manager
        self._dsp       = dispatcher
        self._factory   = factory
        self._validator = validator
        self._stats     = statistics
        self._hist      = history
        self._registry  = registry
        self._listeners = event_listeners

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run_workflow(
        self,
        pipeline: KnowledgePipeline,
        request:  KnowledgeRequest,
    ) -> KnowledgeResponse:
        """
        Execute the full 10-phase workflow.

        Never raises.  Returns a :class:`KnowledgeResponse` on both
        success and failure paths.
        """
        started_at  = time.time()
        session_id  = ""
        errors:     List[str] = []

        pipeline.mark_running()

        try:
            # 1 — Validate Context
            self._add_stage(pipeline, "validate_context", EngineState.INITIALIZING)
            val_results = self._validator.validate_request(request)
            failures    = [r for r in val_results if not r.passed]
            if failures:
                msgs = [r.message for r in failures]
                return self._fail(pipeline, request, msgs, started_at, session_id,
                                  "validation failed")

            # 2 — Initialize Session
            session_id = self._sm.create_session(
                request.knowledge_id, actor=ACTOR_ENGINE
            )
            self._sm.initialize(session_id, actor=ACTOR_ENGINE)
            self._fire(make_knowledge_initialized(
                request.knowledge_id, request.subsystem_id, pipeline.pipeline_id, ACTOR_ENGINE
            ))
            self._stats.record_session()

            # 3 — Start Collection
            self._sm.collect(session_id, actor=ACTOR_ENGINE)
            self._add_stage(pipeline, "start_collection", EngineState.COLLECTING)
            self._fire(make_knowledge_collection_started(
                request.knowledge_id, request.subsystem_id, pipeline.pipeline_id, ACTOR_ENGINE
            ))

            # 4 — Collect Artifacts
            t_collect_start = time.time()
            artifacts       = self._collect_artifacts(request)
            t_collect_ms    = (time.time() - t_collect_start) * 1_000
            self._stats.record_artifacts(
                len(artifacts),
                sources=list(request.sources_requested) or [request.subsystem_id],
            )
            self._stats.record_collection_time(t_collect_ms)
            self._fire(make_knowledge_collected(
                request.knowledge_id, request.subsystem_id, pipeline.pipeline_id, ACTOR_ENGINE
            ))

            # 5 — Validate Artifacts
            self._add_stage(pipeline, "validate_artifacts", EngineState.VALIDATING)
            art_results = self._validator.validate_artifacts(artifacts)
            art_failures = [r for r in art_results if not r.passed]
            if art_failures:
                return self._fail(pipeline, request, [r.message for r in art_failures],
                                  started_at, session_id, "artifact validation failed")
            self._sm.validate_session(session_id, actor=ACTOR_ENGINE)
            self._sm.mark_ready(session_id, actor=ACTOR_ENGINE)
            self._fire(make_knowledge_validated(
                request.knowledge_id, request.subsystem_id, pipeline.pipeline_id, ACTOR_ENGINE
            ))

            # 6 — Classify
            self._add_stage(pipeline, "classify", EngineState.CLASSIFYING)
            classification = self._classify(request, artifacts)
            self._fire(make_knowledge_classified(
                request.knowledge_id, request.subsystem_id, pipeline.pipeline_id, ACTOR_ENGINE
            ))

            # 7 — Dispatch
            self._add_stage(pipeline, "dispatch", EngineState.DISPATCHING)
            self._sm.start_capture(session_id, actor=ACTOR_ENGINE)
            dispatch_result = self._dsp.dispatch(
                knowledge_id  = request.knowledge_id,
                subsystem_id  = request.subsystem_id,
                workflow_type = request.workflow_type,
                artifacts     = artifacts,
                context       = {**request.context.to_dict(), "classification": classification},
            )
            self._sm.mark_indexing_pending(session_id, actor=ACTOR_ENGINE)
            self._fire(make_knowledge_dispatched(
                request.knowledge_id, request.subsystem_id, pipeline.pipeline_id, ACTOR_ENGINE
            ))

            # 8 — Build Snapshot
            self._add_stage(pipeline, "build_snapshot", EngineState.PROCESSING)
            sources = list(request.sources_requested) or [request.subsystem_id]
            snapshot = self._factory.create_snapshot(
                knowledge_id        = request.knowledge_id,
                subsystem_id        = request.subsystem_id,
                session_id          = session_id,
                workflow_type       = request.workflow_type,
                engine_state        = EngineState.PUBLISHING,
                sources_collected   = sources,
                artifacts_collected = len(artifacts),
                artifacts           = artifacts,
                governance_result   = dispatch_result.get("governance_result", {}),
                intelligence_result = dispatch_result.get("intelligence_result", {}),
            )

            # 9 — Publish
            self._add_stage(pipeline, "publish", EngineState.PUBLISHING)
            self._sm.publish(session_id, actor=ACTOR_ENGINE)
            self._stats.record_snapshot()
            self._fire(make_knowledge_published(
                request.knowledge_id, request.subsystem_id, pipeline.pipeline_id, ACTOR_ENGINE
            ))

            # 10 — Complete
            processing_ms = (time.time() - started_at) * 1_000
            self._stats.record_processing_time(processing_ms)
            self._sm.complete_session(session_id, actor=ACTOR_ENGINE)
            pipeline.mark_completed()
            self._registry.close(pipeline)
            self._hist.record(pipeline)
            self._fire(make_knowledge_completed(
                request.knowledge_id, request.subsystem_id, pipeline.pipeline_id, ACTOR_ENGINE
            ))

            return self._factory.success_response(
                request       = request,
                snapshot      = snapshot,
                engine_state  = EngineState.COMPLETED,
                pipeline_id   = pipeline.pipeline_id,
                processing_ms = processing_ms,
            )

        except Exception as exc:  # noqa: BLE001 — manager never raises
            return self._fail(
                pipeline, request, [str(exc)], started_at, session_id,
                reason=f"unexpected error: {type(exc).__name__}",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_artifacts(self, request: KnowledgeRequest) -> Dict[str, Any]:
        """Collect artifacts from request.inputs.  Returns a flat artifact dict."""
        artifacts: Dict[str, Any] = {}
        # Copy provided inputs as artifacts
        for key, value in request.inputs.items():
            if value is not None:
                artifacts[key] = value
        # Add subsystem_id as a source marker if inputs were empty
        if not artifacts:
            artifacts["subsystem_id"] = request.subsystem_id
        return artifacts

    @staticmethod
    def _classify(request: KnowledgeRequest, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Classify the knowledge workflow.  Does NOT perform reasoning."""
        return {
            "workflow_type":    request.workflow_type.value,
            "artifact_count":   len(artifacts),
            "source_count":     len(request.sources_requested) or 1,
            "priority":         int(request.priority),
            "classified_at":    time.time(),
        }

    def _add_stage(
        self,
        pipeline:     KnowledgePipeline,
        name:         str,
        engine_state: EngineState,
    ) -> None:
        stage = PipelineStage(
            stage_name   = name,
            engine_state = engine_state,
            status       = PipelineStatus.COMPLETED,
        )
        pipeline.add_stage(stage)

    def _fire(self, event: KnowledgeEngineEvent) -> None:
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:  # noqa: BLE001
                pass

    def _fail(
        self,
        pipeline:    KnowledgePipeline,
        request:     KnowledgeRequest,
        errors:      List[str],
        started_at:  float,
        session_id:  str,
        reason:      str = "",
    ) -> KnowledgeResponse:
        processing_ms = (time.time() - started_at) * 1_000
        if session_id:
            self._sm.fail_session(session_id, reason=reason, actor=ACTOR_ENGINE)
        pipeline.mark_failed(reason)
        self._registry.close(pipeline)
        self._hist.record(pipeline)
        self._fire(make_knowledge_failed(
            request.knowledge_id,
            request.subsystem_id,
            pipeline.pipeline_id,
            ACTOR_ENGINE,
            reason=reason,
        ))
        return self._factory.failure_response(
            request       = request,
            errors        = errors,
            engine_state  = EngineState.FAILED,
            pipeline_id   = pipeline.pipeline_id,
            processing_ms = processing_ms,
        )
