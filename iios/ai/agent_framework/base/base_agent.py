"""
base_agent.py -- iios.ai.agent_framework.base
==============================================
:class:`BaseAIAgent` — abstract base class for every AI agent.

All specialist agents inherit from this class.  It enforces:

* A mandatory :class:`AgentSpec` declaration.
* A standard activate / suspend / shutdown lifecycle.
* Thread-safe metrics accumulation via immutable :class:`AgentMetrics`.
* A single abstract method :meth:`execute_task` that every agent must implement.

Subclass minimal example::

    class MyAgent(BaseAIAgent):
        def execute_task(
            self,
            task:    AgentTask,
            context: AgentExecutionContext,
        ) -> AgentResult:
            return AgentResult.success(task, {"result": "ok"}, time.time())

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod

from ..core.agent_health      import AgentHealth, HealthStatus
from ..core.agent_metrics     import AgentMetrics
from ..core.agent_spec        import AgentSpec
from ..engine.agent_task       import AgentResult, AgentTask
from ..engine.agent_execution_context import AgentExecutionContext
from ..exceptions              import AIAgentAlreadyRunningError, AIAgentNotRunningError


class BaseAIAgent(ABC):
    """
    Abstract base class for all IIOS AI agents.

    Lifecycle states
    ----------------
    INACTIVE  — created, not yet activated
    ACTIVE    — processing tasks
    SUSPENDED — temporarily paused (not accepting tasks)
    SHUTDOWN  — permanently stopped

    Thread safety
    -------------
    All lifecycle transitions and metrics updates are protected by a
    reentrant lock.  ``execute_task`` is called outside the lock.
    """

    def __init__(self, spec: AgentSpec) -> None:
        self._spec:     AgentSpec    = spec
        self._metrics:  AgentMetrics = spec.initial_metrics()
        self._health:   AgentHealth  = spec.initial_health()
        self._active:   bool         = False
        self._shutdown: bool         = False
        self._lock:     threading.RLock = threading.RLock()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def spec(self) -> AgentSpec:
        return self._spec

    @property
    def agent_id(self) -> str:
        return self._spec.agent_id

    @property
    def agent_name(self) -> str:
        return self._spec.agent_name

    @property
    def agent_type(self) -> str:
        return self._spec.agent_type

    @property
    def is_active(self) -> bool:
        """True when the agent is running and accepting tasks."""
        return self._active and not self._shutdown

    @property
    def is_shutdown(self) -> bool:
        return self._shutdown

    @property
    def metrics(self) -> AgentMetrics:
        """Current (immutable) metrics snapshot."""
        with self._lock:
            return self._metrics

    @property
    def health(self) -> AgentHealth:
        """Current (immutable) health snapshot."""
        with self._lock:
            return self._health

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def activate(self) -> None:
        """
        Transition to ACTIVE state.

        Raises :class:`AIAgentAlreadyRunningError` if already active.
        """
        with self._lock:
            if self._active:
                raise AIAgentAlreadyRunningError(self.agent_id)
            self._active   = True
            self._shutdown = False
            self._health   = AgentHealth.healthy(self.agent_id, "Active")
            self._on_activate()

    def suspend(self) -> None:
        """
        Transition to SUSPENDED state.

        Raises :class:`AIAgentNotRunningError` if not currently active.
        """
        with self._lock:
            if not self._active:
                raise AIAgentNotRunningError(self.agent_id)
            prev_status    = self._health.status.value
            self._active   = False
            self._health   = AgentHealth.degraded(self.agent_id, "Suspended")
            self._on_suspend()

    def resume(self) -> None:
        """
        Transition from SUSPENDED back to ACTIVE.

        Raises :class:`AIAgentAlreadyRunningError` if already active.
        """
        with self._lock:
            if self._active:
                raise AIAgentAlreadyRunningError(self.agent_id)
            if self._shutdown:
                raise AIAgentNotRunningError(self.agent_id)
            self._active = True
            self._health = AgentHealth.healthy(self.agent_id, "Active")
            self._on_resume()

    def shutdown(self) -> None:
        """Permanently stop the agent.  Idempotent."""
        with self._lock:
            self._active   = False
            self._shutdown = True
            self._health   = AgentHealth.unhealthy(self.agent_id, "Shutdown")
            self._on_shutdown()

    # ── Health ────────────────────────────────────────────────────────────────

    def get_health(self) -> AgentHealth:
        """Return the current health snapshot (delegates to ``_check_health``)."""
        with self._lock:
            self._health = self._check_health()
            return self._health

    def set_health(self, health: AgentHealth) -> None:
        """Override health from within a subclass (e.g. after a degraded event)."""
        with self._lock:
            self._health = health

    # ── Metrics (called by AgentExecutionEngine) ──────────────────────────────

    def record_task_assigned(self) -> None:
        with self._lock:
            self._metrics = self._metrics.with_task_assigned()

    def record_task_completed(self, execution_ms: float) -> None:
        with self._lock:
            self._metrics = self._metrics.with_task_completed(execution_ms)

    def record_task_failed(self) -> None:
        with self._lock:
            self._metrics = self._metrics.with_task_failed()

    # ── Abstract methods ──────────────────────────────────────────────────────

    @abstractmethod
    def execute_task(
        self,
        task:    AgentTask,
        context: AgentExecutionContext,
    ) -> AgentResult:
        """
        Execute *task* within *context*.

        Must return an :class:`AgentResult` — either via
        :meth:`AgentResult.success` or :meth:`AgentResult.failure`.
        Must NOT raise.
        """

    # ── Override hooks ────────────────────────────────────────────────────────

    def _on_activate(self) -> None:
        """Called at the end of :meth:`activate`.  Override in subclasses."""

    def _on_suspend(self) -> None:
        """Called at the end of :meth:`suspend`.  Override in subclasses."""

    def _on_resume(self) -> None:
        """Called at the end of :meth:`resume`.  Override in subclasses."""

    def _on_shutdown(self) -> None:
        """Called at the end of :meth:`shutdown`.  Override in subclasses."""

    def _check_health(self) -> AgentHealth:
        """
        Compute the current health state.

        Default implementation returns HEALTHY when active, DEGRADED when
        suspended, UNHEALTHY when shutdown.  Override to add richer checks.
        """
        if self._shutdown:
            return AgentHealth.unhealthy(self.agent_id, "Shutdown")
        if self._active:
            return AgentHealth.healthy(self.agent_id, "Active")
        return AgentHealth.degraded(self.agent_id, "Inactive")

    # ── Repr ─────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        state = "active" if self._active else ("shutdown" if self._shutdown else "inactive")
        return f"<{self.__class__.__name__} id={self.agent_id!r} state={state}>"
