"""
workflow_orchestration_engine.py — iios.workflow.orchestration
--------------------------------------------------------------
WorkflowOrchestrationEngine — top-level coordinator of the
Workflow Orchestration Framework.

Composes all sub-systems into a single execution pipeline:
  Registry → Validator → ResourceManager → Executor → Statistics → History

Provides the public `execute()` method and `WorkflowOrchestrationManager`
wraps it with explicit start/stop lifecycle.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import OrchestrationEventType, PREFIX_ENGINE
from .exceptions import WorkflowExecutionError, WorkflowRegistryError
from .workflow_checkpoint_manager import WorkflowCheckpointManager
from .workflow_compensation_engine import WorkflowCompensationEngine
from .workflow_conditional_engine import WorkflowConditionalEngine, ConditionHandler
from .workflow_definition import WorkflowDefinition, WorkflowExecutionRequest
from .workflow_dependency_engine import WorkflowDependencyEngine
from .workflow_events import OrchestrationEvent, WorkflowOrchestrationEventBus
from .workflow_executor import WorkflowExecutor
from .workflow_factory import WorkflowFactory
from .workflow_history import WorkflowHistory
from .workflow_monitor import WorkflowMonitor
from .workflow_parallel_engine import WorkflowParallelEngine
from .workflow_persistence import WorkflowPersistence
from .workflow_queue_manager import WorkflowQueueManager
from .workflow_recovery_engine import WorkflowRecoveryEngine
from .workflow_registry import WorkflowRegistry
from .workflow_resource_manager import WorkflowResourceManager
from .workflow_runtime import WorkflowExecutionResult
from .workflow_scheduler import WorkflowScheduler
from .workflow_sequential_engine import WorkflowSequentialEngine
from .workflow_state_store import WorkflowStateStore
from .workflow_statistics import WorkflowStatistics
from .workflow_step_executor import StepHandler
from .workflow_validator import WorkflowValidator

_log = get_logger(__name__)

_STATE_STOPPED = "stopped"
_STATE_RUNNING = "running"


class WorkflowOrchestrationEngine:
    """
    Central coordinator for the Workflow Orchestration Framework.

    Orchestrates governance-approved workflows using reusable
    orchestration components.  Performs NO governance evaluation,
    NO business-domain logic, and NO AI reasoning.
    """

    def __init__(
        self,
        *,
        engine_id:        Optional[str]                       = None,
        registry:         Optional[WorkflowRegistry]          = None,
        state_store:      Optional[WorkflowStateStore]        = None,
        statistics:       Optional[WorkflowStatistics]        = None,
        history:          Optional[WorkflowHistory]           = None,
        monitor:          Optional[WorkflowMonitor]           = None,
        event_bus:        Optional[WorkflowOrchestrationEventBus] = None,
        resource_manager: Optional[WorkflowResourceManager]  = None,
        persistence:      Optional[WorkflowPersistence]       = None,
        scheduler:        Optional[WorkflowScheduler]         = None,
        queue_manager:    Optional[WorkflowQueueManager]      = None,
        max_concurrent:   int                                 = 32,
    ) -> None:
        self._engine_id  = engine_id or f"{PREFIX_ENGINE}{uuid.uuid4().hex[:8]}"
        self._registry   = registry         or WorkflowRegistry()
        self._state_store = state_store      or WorkflowStateStore()
        self._statistics = statistics        or WorkflowStatistics()
        self._history    = history           or WorkflowHistory()
        self._event_bus  = event_bus         or WorkflowOrchestrationEventBus()
        self._resource_manager = resource_manager or WorkflowResourceManager(max_concurrent)
        self._persistence = persistence      or WorkflowPersistence()
        self._scheduler  = scheduler         or WorkflowScheduler()
        self._queue_manager = queue_manager  or WorkflowQueueManager()
        self._state      = _STATE_STOPPED
        self._lock       = threading.Lock()

        # Build executor with injected event emitter
        self._executor   = WorkflowExecutor(
            state_store   = self._state_store,
            persistence   = self._persistence,
            event_emitter = self._emit_raw,
        )
        monitor_store = self._state_store
        self._monitor = monitor or WorkflowMonitor(monitor_store)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        with self._lock:
            if self._state == _STATE_RUNNING:
                return
            self._state = _STATE_RUNNING
        self._scheduler.start(executor_fn=self._execute_request)
        self._queue_manager.start(executor_fn=self._execute_request)
        _log.info(f"OrchestrationEngine: initialized engine_id={self._engine_id!r}")

    def stop(self) -> None:
        with self._lock:
            if self._state == _STATE_STOPPED:
                return
            self._state = _STATE_STOPPED
        self._scheduler.stop()
        self._queue_manager.stop()
        _log.info(f"OrchestrationEngine: stopped engine_id={self._engine_id!r}")

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._state == _STATE_RUNNING

    # ── Registration ──────────────────────────────────────────────────────────

    def register_definition(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        validator = WorkflowValidator()
        validator.validate_or_raise(definition)
        self._registry.register_definition(definition)

    def register_handler(self, name: str, handler: StepHandler) -> None:
        self._registry.register_handler(name, handler)

    def register_condition(self, name: str, condition: Callable) -> None:
        self._registry.register_condition(name, condition)

    # ── Execution ─────────────────────────────────────────────────────────────

    def execute(self, request: WorkflowExecutionRequest) -> WorkflowExecutionResult:
        """
        Execute a governance-approved workflow synchronously.

        Acquires a resource slot, runs the workflow to completion,
        updates statistics and history, then releases the slot.

        Never raises for business-level failures; all outcomes are
        expressed in WorkflowExecutionResult.
        """
        self._resource_manager.acquire()
        try:
            result = self._execute_request(request)
        finally:
            self._resource_manager.release()
        return result

    def _execute_request(self, request: WorkflowExecutionRequest) -> WorkflowExecutionResult:
        """Internal: execute without resource management (used by queue/scheduler)."""
        definition = self._registry.get_definition(request.definition_id)

        def handler_lookup(name: str) -> StepHandler:
            return self._registry.get_handler(name)

        def condition_lookup(name: str) -> ConditionHandler:
            return self._registry.get_condition(name)

        result = self._executor.execute(
            request          = request,
            definition       = definition,
            handler_lookup   = handler_lookup,
            condition_lookup = condition_lookup,
        )

        self._history.record(result)
        self._statistics.record_execution(
            status          = result.status,
            duration_ms     = result.duration_ms,
            steps_executed  = result.steps_executed,
            steps_succeeded = result.steps_succeeded,
            steps_failed    = result.steps_failed,
            retries         = result.retries,
            compensations   = result.compensations,
            checkpoints     = result.checkpoints,
        )
        return result

    # ── Async execution via queue ─────────────────────────────────────────────

    def enqueue(self, request: WorkflowExecutionRequest) -> str:
        """Submit request to queue for async execution.  Returns job_id."""
        return self._queue_manager.enqueue(request)

    # ── Scheduling ────────────────────────────────────────────────────────────

    def schedule_once(
        self,
        definition_id:  str,
        delay_seconds:  float,
        *,
        context_data:   Optional[Dict[str, Any]] = None,
    ) -> str:
        return self._scheduler.schedule_once(
            definition_id, delay_seconds, context_data=context_data
        )

    def schedule_recurring(
        self,
        definition_id:    str,
        interval_seconds: float,
        *,
        context_data:     Optional[Dict[str, Any]] = None,
        initial_delay:    float                    = 0.0,
    ) -> str:
        return self._scheduler.schedule_recurring(
            definition_id, interval_seconds,
            initial_delay=initial_delay, context_data=context_data
        )

    def cancel_job(self, job_id: str) -> bool:
        return self._scheduler.cancel(job_id)

    # ── Event helpers ─────────────────────────────────────────────────────────

    def _emit_raw(
        self,
        event_type: OrchestrationEventType,
        payload:    Dict[str, Any],
    ) -> None:
        event = OrchestrationEvent.create(
            event_type  = event_type,
            engine_id   = self._engine_id,
            workflow_id = payload.get("workflow_id", ""),
            runtime_id  = payload.get("runtime_id", ""),
            payload     = payload,
        )
        self._event_bus.emit(event)

    # ── Introspection ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        return {
            "engine_id":       self._engine_id,
            "state":           self._state,
            "is_running":      self.is_running,
            "definitions":     self._registry.definition_count(),
            "handlers":        self._registry.handler_count(),
            "active_workflows": self._monitor.active_count(),
            "total_workflows": self._monitor.total_count(),
            "resources":       self._resource_manager.health(),
            "queue_size":      self._queue_manager.queue_size(),
            "scheduled_jobs":  self._scheduler.job_count(),
        }

    def status(self) -> Dict[str, Any]:
        return self.health()

    def statistics(self) -> Dict[str, Any]:
        return self._statistics.report().to_dict()

    def history(self) -> WorkflowHistory:
        return self._history

    def monitor(self) -> WorkflowMonitor:
        return self._monitor

    def event_bus(self) -> WorkflowOrchestrationEventBus:
        return self._event_bus

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @property
    def registry(self) -> WorkflowRegistry:
        return self._registry
