"""
knowledge_engine.py — iios.knowledge.engine
---------------------------------------------
PRIMARY PUBLIC INTERFACE for the Knowledge Engine.

Responsibilities (this module ONLY):
  - Accept knowledge workflow requests via submit()
  - Wire and coordinate all engine subsystems
  - Expose health(), status(), statistics(), query() introspection
  - Support scheduler-based and direct collection

This module NEVER:
  - Performs knowledge reasoning (M4 responsibility)
  - Evaluates governance policies (M3 responsibility)
  - Performs semantic search or embedding generation
  - Communicates with AI/ML models directly
  - Accesses vector databases

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_SCHEDULER_QUEUE,
    ENGINE_SYSTEM_ID,
    EngineState,
    KnowledgeWorkflowType,
    SchedulerMode,
    SchedulerPriority,
    VERSION,
)
from .exceptions import KnowledgeEngineNotRunningError
from .knowledge_context import KnowledgeEngineContext
from .knowledge_dispatcher import KnowledgeDispatcher, GovernanceDelegate, IntelligenceDelegate
from .knowledge_events import KnowledgeEngineEventBus
from .knowledge_factory import KnowledgeEngineFactory
from .knowledge_health import KnowledgeEngineHealth
from .knowledge_history import KnowledgeEngineHistory
from .knowledge_manager import KnowledgeWorkflowManager
from .knowledge_pipeline import KnowledgePipeline
from .knowledge_registry import KnowledgeEngineRegistry
from .knowledge_request import KnowledgeRequest
from .knowledge_response import KnowledgeResponse, KnowledgeSnapshot
from .knowledge_scheduler import KnowledgeScheduler
from .knowledge_session_manager import KnowledgeSessionManager
from .knowledge_statistics import KnowledgeEngineStatistics
from .knowledge_status import KnowledgeEngineStatus
from .knowledge_validation import KnowledgeEngineValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class KnowledgeEngine(LifecycleAwareMixin):
    """
    Institutional Knowledge Engine.

    Orchestrates knowledge workflows through a 10-phase pipeline:
    Validate → Initialize → Collect → Validate Artifacts → Classify
    → Dispatch → Build Snapshot → Publish → Complete.

    Parameters
    ----------
    session_manager :   Injected KnowledgeSessionManager (optional).
    scheduler :         Injected KnowledgeScheduler (optional).
    dispatcher :        Injected KnowledgeDispatcher (optional).
    registry :          Injected KnowledgeEngineRegistry (optional).
    factory :           Injected KnowledgeEngineFactory (optional).
    validator :         Injected KnowledgeEngineValidator (optional).
    health :            Injected KnowledgeEngineHealth (optional).
    statistics :        Injected KnowledgeEngineStatistics (optional).
    history :           Injected KnowledgeEngineHistory (optional).
    manager :           Injected KnowledgeWorkflowManager (optional).
    lifecycle :         Injected M1 KnowledgeLifecycle (optional).
    governance_delegate : Injected M3 governance callable (optional).
    intelligence_delegate : Injected M4 intelligence callable (optional).
    max_sessions :      Maximum concurrent lifecycle sessions.
    max_pipelines :     Maximum active pipelines.
    max_queue :         Maximum scheduler queue depth.
    """

    def __init__(
        self,
        session_manager:       Optional[KnowledgeSessionManager]  = None,
        scheduler:             Optional[KnowledgeScheduler]        = None,
        dispatcher:            Optional[KnowledgeDispatcher]       = None,
        registry:              Optional[KnowledgeEngineRegistry]   = None,
        factory:               Optional[KnowledgeEngineFactory]    = None,
        validator:             Optional[KnowledgeEngineValidator]  = None,
        health:                Optional[KnowledgeEngineHealth]     = None,
        statistics:            Optional[KnowledgeEngineStatistics] = None,
        history:               Optional[KnowledgeEngineHistory]    = None,
        manager:               Optional[KnowledgeWorkflowManager]  = None,
        *,
        lifecycle:             Optional[Any]                       = None,
        governance_delegate:   Optional[GovernanceDelegate]        = None,
        intelligence_delegate: Optional[IntelligenceDelegate]      = None,
        max_sessions:  int   = DEFAULT_MAX_CONCURRENT_SESSIONS,
        max_pipelines: int   = DEFAULT_MAX_PIPELINES,
        max_queue:     int   = DEFAULT_MAX_SCHEDULER_QUEUE,
        max_history:   int   = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._max_sessions  = max_sessions
        self._max_pipelines = max_pipelines
        self._max_queue     = max_queue
        self._start_ts:     Optional[float] = None

        # -- Subsystem construction ------------------------------------------
        self._session_mgr = session_manager or KnowledgeSessionManager(lifecycle=lifecycle)
        self._scheduler   = scheduler or KnowledgeScheduler(max_queue_size=max_queue)
        self._dispatcher  = dispatcher or KnowledgeDispatcher(
            governance_delegate   = governance_delegate,
            intelligence_delegate = intelligence_delegate,
        )
        self._registry  = registry  or KnowledgeEngineRegistry(
            max_pipelines = max_pipelines
        )
        self._factory   = factory   or KnowledgeEngineFactory()
        self._validator = validator or KnowledgeEngineValidator(
            max_sessions    = max_sessions,
            active_count_fn = self._active_session_count,
        )
        self._health_rep = health or KnowledgeEngineHealth(
            session_manager = self._session_mgr,
            dispatcher      = self._dispatcher,
            scheduler       = self._scheduler,
            registry        = self._registry,
        )
        self._stats   = statistics or KnowledgeEngineStatistics()
        self._hist    = history    or KnowledgeEngineHistory(max_entries=max_history)
        self._bus     = KnowledgeEngineEventBus()

        # -- Listeners -------------------------------------------------------
        self._listeners: List[Callable] = []
        self._listener_lock = threading.Lock()

        # -- Workflow manager ------------------------------------------------
        self._manager = manager or KnowledgeWorkflowManager(
            session_manager = self._session_mgr,
            dispatcher      = self._dispatcher,
            factory         = self._factory,
            validator       = self._validator,
            statistics      = self._stats,
            history         = self._hist,
            registry        = self._registry,
            event_listeners = self._listeners,
        )

        # -- Current engine state (not LifecycleAwareMixin state) -----------
        self._engine_state  = EngineState.IDLE
        self._engine_lock   = threading.Lock()

    # ------------------------------------------------------------------
    # LifecycleAwareMixin hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._start_ts = time.time()
        self._scheduler.start()
        self._engine_state = EngineState.IDLE
        _log.info(f"KnowledgeEngine started — version={VERSION}")

    def _on_stop(self) -> None:
        self._scheduler.stop()
        self._engine_state = EngineState.STOPPED
        _log.info(f"KnowledgeEngine stopped")

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _require_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise KnowledgeEngineNotRunningError()

    def _active_session_count(self) -> int:
        return self._session_mgr.active_count()

    # ------------------------------------------------------------------
    # Primary submit interface
    # ------------------------------------------------------------------

    def submit(self, request: KnowledgeRequest) -> KnowledgeResponse:
        """
        Submit a knowledge workflow request for immediate synchronous execution.

        This is the primary entry point for all knowledge workflows.
        """
        self._require_running()
        pipeline = self._factory.create_pipeline(request)
        self._registry.register(pipeline)
        with self._engine_lock:
            self._engine_state = EngineState.INITIALIZING
        try:
            response = self._manager.run_workflow(pipeline, request)
            with self._engine_lock:
                self._engine_state = EngineState.IDLE
            return response
        except Exception as exc:  # noqa: BLE001 — belt-and-suspenders
            with self._engine_lock:
                self._engine_state = EngineState.IDLE
            _log.warning(f"KnowledgeEngine.submit unexpected error: {exc!r}")
            return self._factory.failure_response(
                request       = request,
                errors        = [str(exc)],
                engine_state  = EngineState.FAILED,
                pipeline_id   = pipeline.pipeline_id,
                processing_ms = 0.0,
            )

    def schedule(self, request: KnowledgeRequest) -> bool:
        """
        Schedule a knowledge request for deferred processing.

        Returns ``True`` if the request was accepted into the queue.
        """
        self._require_running()
        return self._scheduler.enqueue(request)

    def schedule_batch(self, requests: List[KnowledgeRequest]) -> int:
        """Schedule a batch of requests.  Returns accepted count."""
        self._require_running()
        return self._scheduler.enqueue_batch(requests)

    def process_next(self) -> Optional[KnowledgeResponse]:
        """
        Dequeue and process the next scheduled request (if any).

        Returns ``None`` if the queue is empty.
        """
        self._require_running()
        request = self._scheduler.dequeue(timeout=0.0)
        if request is None:
            return None
        return self.submit(request)

    # ------------------------------------------------------------------
    # Delegate registration
    # ------------------------------------------------------------------

    def set_governance_delegate(self, delegate: GovernanceDelegate) -> None:
        """Register the M3 Knowledge Governance Policy Framework delegate."""
        self._dispatcher.set_governance_delegate(delegate)

    def set_intelligence_delegate(self, delegate: IntelligenceDelegate) -> None:
        """Register the M4 Knowledge Intelligence Framework delegate."""
        self._dispatcher.set_intelligence_delegate(delegate)

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    def add_listener(self, listener: Callable) -> None:
        with self._listener_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> bool:
        with self._listener_lock:
            try:
                self._listeners.remove(listener)
                return True
            except ValueError:
                return False

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return a health-check dictionary."""
        return self._health_rep.assess(
            engine_state = self.lifecycle_state().value,
            statistics   = self._stats.snapshot(),
        )

    def status(self) -> Dict[str, Any]:
        """Return a detailed engine status dictionary."""
        uptime = (time.time() - self._start_ts) if self._start_ts else 0.0
        return KnowledgeEngineStatus.build(
            lifecycle_state   = self.lifecycle_state().value,
            engine_state      = self._engine_state,
            active_sessions   = self._session_mgr.active_count(),
            active_pipelines  = self._registry.active_count(),
            archived_pipelines = self._registry.archived_count(),
            scheduler_depth   = self._scheduler.queue_depth(),
            statistics        = self._stats.snapshot(),
            recent_history    = self._hist.recent(20),
            uptime_seconds    = uptime,
        )

    def statistics(self) -> Dict[str, Any]:
        """Return a snapshot of all 7 statistics counters."""
        return self._stats.snapshot()

    def history(self, n: int = 20) -> List[KnowledgePipeline]:
        """Return the *n* most recent completed pipelines."""
        return self._hist.recent(n)

    def query(self, knowledge_id: str) -> Optional[KnowledgePipeline]:
        """Look up a pipeline by knowledge_id (first match in history)."""
        for p in self._hist.for_knowledge_id(knowledge_id):
            return p
        return None

    def engine_state(self) -> EngineState:
        """Current processing state of the engine."""
        with self._engine_lock:
            return self._engine_state
