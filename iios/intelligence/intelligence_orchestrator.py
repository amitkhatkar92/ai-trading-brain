"""
iios/intelligence/intelligence_orchestrator.py
==============================================
IntelligenceOrchestrator — the mandatory coordination gateway for all
AI capabilities within IIOS.

Rule: NO AI engine communicates directly with another AI engine.
      EVERY intelligence workflow passes through this orchestrator.

Public API
----------
initialize()                          → IntelligenceOrchestrator
register_engine(...)                  → EngineDescriptor
call_engine(engine_id, request)       → Any
call_best_engine(engine_type, req)    → Any
create_session(...)                   → IntelligenceSession
run_workflow(workflow_id, context)    → WorkflowRunResult
run_definition(defn, context)         → WorkflowRunResult
register_workflow(defn)               → None
schedule_workflow(...)                → ScheduledWorkflow
trigger_schedule(schedule_id)         → WorkflowRunResult
workflow_builder(id)                  → WorkflowBuilder
register_policy(policy_type, policy)  → None
stats()                               → dict
health()                              → dict

Singleton: get_intelligence_orchestrator() / reset_intelligence_orchestrator()
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from .intelligence_constants import (
    EngineType,
    Priority,
    OrchestratorStatus,
    PolicyType,
    SYSTEM_ACTOR,
    INTELLIGENCE_ENGINE_VERSION,
)
from .intelligence_exceptions import OrchestratorNotInitializedError, PolicyViolationError
from .intelligence_manager  import IntelligenceManager, get_intelligence_manager
from .registry.engine_registry import EngineDescriptor
from .sessions.intelligence_session import IntelligenceSession
from .sessions.session_result import SessionResult
from .workflow.workflow_builder  import WorkflowBuilder, WorkflowDefinition
from .workflow.workflow_executor import WorkflowRunResult
from .workflow.workflow_scheduler import ScheduledWorkflow
from .execution.execution_policy import ExecutionPolicy

log = logging.getLogger(__name__)

__all__ = [
    "IntelligenceOrchestrator",
    "get_intelligence_orchestrator",
    "reset_intelligence_orchestrator",
]


class IntelligenceOrchestrator:
    """
    Single entry-point for all intelligence operations in IIOS.

    Wraps IntelligenceManager and adds:
      - Orchestration policies (priority, retry, fallback, etc.)
      - Policy enforcement
      - Version/health metadata
      - Structured logging integration
    """

    def __init__(self, manager: Optional[IntelligenceManager] = None) -> None:
        self._manager  = manager or get_intelligence_manager()
        self._policies: dict[PolicyType, Any] = {}
        self._lock     = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> "IntelligenceOrchestrator":
        log.info(
            "Initializing IntelligenceOrchestrator v%s",
            INTELLIGENCE_ENGINE_VERSION,
        )
        self._manager.initialize()
        log.info("IntelligenceOrchestrator ready")
        return self

    def shutdown(self) -> None:
        log.info("Shutting down IntelligenceOrchestrator")
        self._manager.shutdown()

    @property
    def is_initialized(self) -> bool:
        return self._manager.is_initialized

    @property
    def version(self) -> str:
        return INTELLIGENCE_ENGINE_VERSION

    # ── Policy management ─────────────────────────────────────────────────────

    def register_policy(self, policy_type: PolicyType, policy: Any) -> None:
        with self._lock:
            self._policies[policy_type] = policy

    def get_policy(self, policy_type: PolicyType) -> Optional[Any]:
        with self._lock:
            return self._policies.get(policy_type)

    def _check_priority(self, priority: Priority) -> None:
        """Enforce minimum priority policy if registered."""
        min_pri = self._policies.get(PolicyType.PRIORITY)
        if min_pri is not None and priority.value < min_pri.value:
            raise PolicyViolationError(
                PolicyType.PRIORITY.value,
                f"priority {priority.name} below minimum {min_pri.name}",
            )

    # ── Engine operations ─────────────────────────────────────────────────────

    def register_engine(
        self,
        engine_id:   str,
        engine_type: EngineType,
        name:        str,
        factory:     Optional[Callable] = None,
        instance:    Any                = None,
        version:     str                = "1.0.0",
        priority:    Priority           = Priority.NORMAL,
        overwrite:   bool               = False,
    ) -> EngineDescriptor:
        log.debug("Registering engine %r (%s)", engine_id, engine_type.value)
        return self._manager.register_engine(
            engine_id=engine_id, engine_type=engine_type, name=name,
            factory=factory, instance=instance, version=version,
            priority=priority, overwrite=overwrite,
        )

    def call_engine(
        self,
        engine_id:  str,
        request:    Any   = None,
        priority:   Priority = Priority.NORMAL,
        timeout_ms: float = 60_000.0,
    ) -> Any:
        """
        Invoke a specific engine by ID.

        All engine calls MUST use this method.
        Direct engine.execute() calls are forbidden outside this orchestrator.
        """
        self._check_priority(priority)
        log.debug("Calling engine %r", engine_id)
        return self._manager.call_engine(engine_id, request, timeout_ms=timeout_ms)

    def call_best_engine(
        self,
        engine_type: EngineType,
        request:     Any     = None,
        priority:    Priority = Priority.NORMAL,
    ) -> Any:
        self._check_priority(priority)
        return self._manager.call_best_engine(engine_type, request)

    # ── Session operations ────────────────────────────────────────────────────

    def create_session(
        self,
        actor:    str           = SYSTEM_ACTOR,
        priority: Priority      = Priority.NORMAL,
        tags:     list[str] | None = None,
        metadata: dict | None   = None,
    ) -> IntelligenceSession:
        self._check_priority(priority)
        return self._manager.create_session(
            actor=actor, priority=priority, tags=tags, metadata=metadata
        )

    def complete_session(
        self,
        session_id: str,
        result:     Optional[SessionResult] = None,
    ) -> IntelligenceSession:
        return self._manager.complete_session(session_id, result)

    def fail_session(self, session_id: str, reason: str = "") -> IntelligenceSession:
        return self._manager.fail_session(session_id, reason)

    def get_session(self, session_id: str) -> IntelligenceSession:
        return self._manager.get_session(session_id)

    # ── Workflow operations ───────────────────────────────────────────────────

    def register_workflow(
        self,
        definition: WorkflowDefinition,
        overwrite:  bool = False,
    ) -> None:
        log.debug("Registering workflow %r", definition.workflow_id)
        self._manager.register_workflow(definition, overwrite=overwrite)

    def run_workflow(
        self,
        workflow_id: str,
        context:     dict[str, Any] | None = None,
        priority:    Priority              = Priority.NORMAL,
    ) -> WorkflowRunResult:
        self._check_priority(priority)
        log.debug("Running workflow %r", workflow_id)
        return self._manager.run_workflow(workflow_id, context=context)

    def run_definition(
        self,
        definition: WorkflowDefinition,
        context:    dict[str, Any] | None = None,
        priority:   Priority              = Priority.NORMAL,
    ) -> WorkflowRunResult:
        self._check_priority(priority)
        return self._manager.run_workflow_definition(definition, context=context)

    def workflow_builder(self, workflow_id: Optional[str] = None) -> WorkflowBuilder:
        return self._manager._workflows.builder(workflow_id)

    # ── Scheduling ────────────────────────────────────────────────────────────

    def schedule_workflow(
        self,
        definition: WorkflowDefinition,
        interval_s: Optional[float]     = None,
        delay_s:    float               = 0.0,
        context:    dict | None         = None,
        max_runs:   Optional[int]       = None,
        on_complete: Optional[Callable] = None,
    ) -> ScheduledWorkflow:
        wfe = self._manager._workflows
        if interval_s is not None:
            return wfe.schedule_interval(
                definition, interval_s=interval_s, delay_s=delay_s,
                context=context, max_runs=max_runs,
            )
        return wfe.schedule_once(
            definition, delay_s=delay_s, context=context, on_complete=on_complete
        )

    def trigger_schedule(self, schedule_id: str) -> WorkflowRunResult:
        return self._manager._workflows.trigger(schedule_id)

    def cancel_schedule(self, schedule_id: str) -> bool:
        return self._manager._workflows.cancel_schedule(schedule_id)

    # ── Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        s = self._manager.stats()
        s["orchestrator_version"] = INTELLIGENCE_ENGINE_VERSION
        return s

    def health(self) -> dict:
        h = self._manager.health()
        h["orchestrator_version"] = INTELLIGENCE_ENGINE_VERSION
        return h


# ── Singleton ─────────────────────────────────────────────────────────────────

_orch_lock = threading.Lock()
_orch_inst: Optional[IntelligenceOrchestrator] = None


def get_intelligence_orchestrator() -> IntelligenceOrchestrator:
    global _orch_inst
    if _orch_inst is None:
        with _orch_lock:
            if _orch_inst is None:
                _orch_inst = IntelligenceOrchestrator()
    return _orch_inst


def reset_intelligence_orchestrator() -> None:
    global _orch_inst
    with _orch_lock:
        if _orch_inst is not None:
            try:
                _orch_inst.shutdown()
            except Exception:
                pass
        _orch_inst = None
