"""
iios/intelligence/intelligence_manager.py
==========================================
IntelligenceManager — the coordination hub of the Intelligence Layer.

Orchestrates:
  - EngineRegistry      (AI engine registration / discovery)
  - SessionManager      (session lifecycle)
  - WorkflowEngine      (workflow execution / scheduling)
  - IntelligenceContext (thread-local execution tracking)
  - Metrics collection  (execution stats)

Every AI engine call and workflow execution flows through this manager.

Singleton: get_intelligence_manager() / reset_intelligence_manager()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .intelligence_constants import (
    EngineType,
    EngineStatus,
    Priority,
    SessionStatus,
    OrchestratorStatus,
    SYSTEM_ACTOR,
)
from .intelligence_exceptions import (
    OrchestratorNotInitializedError,
    EngineNotFoundError,
    EngineExecutionError,
    EngineUnavailableError,
)
from .intelligence_context import IntelligenceContext, get_intelligence_context
from .registry.engine_registry import (
    EngineRegistry,
    EngineDescriptor,
    get_engine_registry,
)
from .sessions.session_manager import SessionManager, get_session_manager
from .sessions.intelligence_session import IntelligenceSession
from .sessions.session_result import SessionResult
from .workflow.workflow_engine import WorkflowEngine, get_workflow_engine
from .workflow.workflow_builder import WorkflowDefinition
from .workflow.workflow_executor import WorkflowRunResult

log = logging.getLogger(__name__)

__all__ = [
    "IntelligenceStats",
    "IntelligenceManager",
    "get_intelligence_manager",
    "reset_intelligence_manager",
]


@dataclass
class IntelligenceStats:
    """Runtime metrics for the intelligence layer."""
    total_sessions:     int    = 0
    total_workflows:    int    = 0
    total_engine_calls: int    = 0
    failed_calls:       int    = 0
    total_ms:           float  = 0.0
    started_at:         float  = field(default_factory=time.time)

    @property
    def avg_ms(self) -> float:
        calls = self.total_engine_calls + self.total_workflows
        return self.total_ms / calls if calls else 0.0

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.started_at

    def record_call(self, duration_ms: float, failed: bool = False) -> None:
        self.total_engine_calls += 1
        self.total_ms           += duration_ms
        if failed:
            self.failed_calls += 1

    def record_workflow(self, duration_ms: float) -> None:
        self.total_workflows += 1
        self.total_ms        += duration_ms

    def to_dict(self) -> dict:
        return {
            "total_sessions":     self.total_sessions,
            "total_workflows":    self.total_workflows,
            "total_engine_calls": self.total_engine_calls,
            "failed_calls":       self.failed_calls,
            "avg_ms":             round(self.avg_ms, 3),
            "uptime_seconds":     round(self.uptime_seconds, 1),
        }


class IntelligenceManager:
    """
    Coordination hub that every intelligence operation passes through.
    """

    def __init__(
        self,
        engine_registry:  Optional[EngineRegistry]  = None,
        session_manager:  Optional[SessionManager]  = None,
        workflow_engine:  Optional[WorkflowEngine]  = None,
        context:          Optional[IntelligenceContext] = None,
    ) -> None:
        self._engines   = engine_registry or get_engine_registry()
        self._sessions  = session_manager or get_session_manager()
        self._workflows = workflow_engine or get_workflow_engine()
        self._ctx       = context or get_intelligence_context()
        self._stats     = IntelligenceStats()
        self._status    = OrchestratorStatus.UNINITIALIZED
        self._lock      = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> "IntelligenceManager":
        with self._lock:
            self._status = OrchestratorStatus.INITIALIZING
            self._workflows.initialize()
            self._status = OrchestratorStatus.READY
            log.info("IntelligenceManager initialized")
        return self

    def shutdown(self) -> None:
        with self._lock:
            self._status = OrchestratorStatus.SHUTTING_DOWN
            try:
                self._workflows.stop_scheduler()
            except Exception:
                pass
            self._status = OrchestratorStatus.STOPPED
            log.info("IntelligenceManager shut down")

    @property
    def is_initialized(self) -> bool:
        return self._status == OrchestratorStatus.READY

    @property
    def status(self) -> OrchestratorStatus:
        return self._status

    def _require_init(self) -> None:
        if self._status not in (OrchestratorStatus.READY, OrchestratorStatus.DEGRADED):
            raise OrchestratorNotInitializedError()

    # ── Engine management ─────────────────────────────────────────────────────

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
        if instance is not None:
            desc = self._engines.register_instance(
                engine_id=engine_id, engine_type=engine_type,
                name=name, instance=instance, version=version,
                priority=priority, overwrite=overwrite,
            )
        elif factory is not None:
            desc = self._engines.register_factory(
                engine_id=engine_id, engine_type=engine_type,
                name=name, factory=factory, version=version,
                priority=priority, overwrite=overwrite,
            )
        else:
            from .registry.engine_registry import EngineDescriptor
            desc = EngineDescriptor(
                engine_id=engine_id, engine_type=engine_type,
                name=name, version=version, priority=priority,
            )
            self._engines.register(desc, overwrite=overwrite)
        return desc

    def call_engine(
        self,
        engine_id: str,
        request:   Any = None,
        timeout_ms: float = 60_000.0,
    ) -> Any:
        """
        Call a registered engine by ID.

        All AI engine invocations must use this method — never call
        engine.execute() directly from outside the intelligence layer.
        """
        self._require_init()
        desc = self._engines.get(engine_id)
        if desc.status == EngineStatus.DISABLED:
            raise EngineUnavailableError(engine_id, "disabled")
        t0 = time.perf_counter()
        try:
            inst   = desc.get_instance()
            result = inst.execute(request)
            ms     = (time.perf_counter() - t0) * 1_000
            self._stats.record_call(ms)
            return result
        except EngineUnavailableError:
            raise
        except Exception as exc:
            ms = (time.perf_counter() - t0) * 1_000
            self._stats.record_call(ms, failed=True)
            raise EngineExecutionError(engine_id, str(exc)) from exc

    def call_best_engine(
        self,
        engine_type: EngineType,
        request:     Any = None,
    ) -> Any:
        """Call the highest-priority READY engine of the given type."""
        self._require_init()
        desc = self._engines.best(engine_type)
        if desc is None:
            raise EngineNotFoundError(engine_type.value)
        return self.call_engine(desc.engine_id, request)

    # ── Session management ────────────────────────────────────────────────────

    def create_session(
        self,
        actor:    str           = SYSTEM_ACTOR,
        priority: Priority      = Priority.NORMAL,
        tags:     list[str] | None = None,
        metadata: dict | None   = None,
    ) -> IntelligenceSession:
        self._require_init()
        s = self._sessions.create(actor=actor, priority=priority,
                                  tags=tags, metadata=metadata)
        self._stats.total_sessions += 1
        return s

    def complete_session(
        self,
        session_id: str,
        result:     Optional[SessionResult] = None,
    ) -> IntelligenceSession:
        return self._sessions.complete(session_id, result)

    def fail_session(self, session_id: str, reason: str = "") -> IntelligenceSession:
        return self._sessions.fail(session_id, reason)

    def get_session(self, session_id: str) -> IntelligenceSession:
        return self._sessions.get(session_id)

    # ── Workflow execution ────────────────────────────────────────────────────

    def run_workflow(
        self,
        workflow_id: str,
        context:     dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        self._require_init()
        t0  = time.perf_counter()
        res = self._workflows.run(workflow_id, context=context)
        self._stats.record_workflow((time.perf_counter() - t0) * 1_000)
        return res

    def run_workflow_definition(
        self,
        definition: WorkflowDefinition,
        context:    dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        self._require_init()
        t0  = time.perf_counter()
        res = self._workflows.run_definition(definition, context=context)
        self._stats.record_workflow((time.perf_counter() - t0) * 1_000)
        return res

    def register_workflow(
        self,
        definition: WorkflowDefinition,
        overwrite:  bool = False,
    ) -> None:
        self._workflows.register(definition, overwrite=overwrite)

    # ── Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "status":    self._status.value,
            "engine":    self._engines.stats(),
            "sessions":  self._sessions.stats(),
            "workflows": self._workflows.stats(),
            "metrics":   self._stats.to_dict(),
        }

    def health(self) -> dict:
        return {
            "status":      self._status.value,
            "initialized": self.is_initialized,
            "engines":     self._engines.stats()["total"],
            "sessions":    self._sessions.stats()["active"],
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_mgr_lock = threading.Lock()
_mgr_inst: Optional[IntelligenceManager] = None


def get_intelligence_manager() -> IntelligenceManager:
    global _mgr_inst
    if _mgr_inst is None:
        with _mgr_lock:
            if _mgr_inst is None:
                _mgr_inst = IntelligenceManager()
    return _mgr_inst


def reset_intelligence_manager() -> None:
    global _mgr_inst
    with _mgr_lock:
        if _mgr_inst is not None:
            try:
                _mgr_inst.shutdown()
            except Exception:
                pass
        _mgr_inst = None
