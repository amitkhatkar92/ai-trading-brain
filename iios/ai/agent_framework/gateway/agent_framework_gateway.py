"""
agent_framework_gateway.py -- iios.ai.agent_framework.gateway
===============================================================
:class:`AgentFrameworkGateway` — the single public entry point for A5.

This is an M6 Gateway.  It:
* Inherits :class:`AILifecycleAwareMixin` from A1.
* Owns an :class:`AgentFrameworkContainer` (wired in ``_on_initialize``).
* Exposes a stable, versioned public API.
* Provides ``health()``, ``status()``, ``snapshot()`` consistent with A2–A4.

Public API
----------
register_agent(agent)             → AgentDescriptor
create_and_register(spec)         → BaseAIAgent
find_agent(agent_id)              → BaseAIAgent
start_agent(agent_id)             → None
stop_agent(agent_id)              → None
suspend_agent(agent_id)           → None
resume_agent(agent_id)            → None
assign_task(task)                 → AgentResult
list_agents()                     → List[AgentDescriptor]
find_agents_by_capability(type)   → List[AgentDescriptor]
get_agent_health(agent_id)        → AgentHealth
get_agent_metrics(agent_id)       → AgentMetrics
health()                          → Dict[str, Any]
status()                          → Dict[str, Any]
snapshot()                        → AgentFrameworkSnapshot

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from ..container.agent_framework_container import AgentFrameworkContainer
from ..core.agent_capabilities             import CapabilityType
from ..core.agent_health                   import AgentHealth
from ..core.agent_metrics                  import AgentMetrics
from ..core.agent_spec                     import AgentSpec
from ..engine.agent_task                   import AgentResult, AgentTask
from ..lifecycle                           import AILifecycleAwareMixin
from ..registry.agent_descriptor           import AgentDescriptor
from ..snapshot.agent_snapshot             import AgentFrameworkSnapshot

# Avoid importing BaseAIAgent at module level to prevent circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..base.base_agent import BaseAIAgent

_log = get_logger(__name__)


class AgentFrameworkGateway(AILifecycleAwareMixin):
    """
    M6 Public gateway for the A5 AI Agent Framework.

    Usage::

        gw = AgentFrameworkGateway()
        gw.initialize()
        gw.start()

        spec  = AgentSpec.create(identity)
        agent = gw.create_and_register(spec)
        gw.start_agent(agent.agent_id)

        task   = AgentTask.create(agent.agent_id, "analyse_market", payload={})
        result = gw.assign_task(task)
    """

    SYSTEM_ID: str = "iios:ai:agent_framework:gateway"
    VERSION:   str = "1.0.0"

    def __init__(
        self,
        container: Optional[AgentFrameworkContainer] = None,
    ) -> None:
        self._container:  AgentFrameworkContainer = container or AgentFrameworkContainer()
        self._started_at: Optional[float]          = None

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def _on_initialize(self) -> None:
        self._container.build()
        _log.info("AgentFrameworkGateway: container built")

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info("AgentFrameworkGateway: started")

    def _on_stop(self) -> None:
        _log.info("AgentFrameworkGateway: stopped")

    # ── Agent Registration API ────────────────────────────────────────────────

    def register_agent(self, agent: "BaseAIAgent") -> AgentDescriptor:
        """Register an already-constructed agent.  Returns its descriptor."""
        return self._container.agent_manager.register_agent(agent)

    def create_and_register(self, spec: AgentSpec) -> "BaseAIAgent":
        """Create an agent from *spec* via the factory and register it."""
        return self._container.agent_manager.create_and_register(spec)

    # ── Agent Discovery API ───────────────────────────────────────────────────

    def find_agent(self, agent_id: str) -> "BaseAIAgent":
        """Return the live agent registered under *agent_id*."""
        return self._container.agent_manager.find_agent(agent_id)

    def list_agents(self) -> List[AgentDescriptor]:
        """Return descriptors for all registered agents."""
        return self._container.agent_manager.list_agents()

    def find_agents_by_capability(
        self,
        capability_type: CapabilityType,
    ) -> List[AgentDescriptor]:
        """Return descriptors for all agents that have *capability_type*."""
        return self._container.agent_manager.find_agents_by_capability(capability_type)

    # ── Agent Lifecycle API ───────────────────────────────────────────────────

    def start_agent(self, agent_id: str) -> None:
        """Activate the agent.  Publishes AgentStartedEvent."""
        self._container.agent_manager.start_agent(agent_id)

    def stop_agent(self, agent_id: str) -> None:
        """Permanently shut down the agent.  Publishes AgentStoppedEvent."""
        self._container.agent_manager.stop_agent(agent_id)

    def suspend_agent(self, agent_id: str) -> None:
        """Temporarily suspend the agent.  Publishes AgentSuspendedEvent."""
        self._container.agent_manager.suspend_agent(agent_id)

    def resume_agent(self, agent_id: str) -> None:
        """Resume a suspended agent.  Publishes AgentResumedEvent."""
        self._container.agent_manager.resume_agent(agent_id)

    # ── Task Execution API ────────────────────────────────────────────────────

    def assign_task(self, task: AgentTask) -> AgentResult:
        """
        Dispatch *task* to the target agent and return the result.

        Publishes TaskAssigned, TaskStarted, and TaskCompleted/TaskFailed events.
        """
        return self._container.execution_engine.assign_task(task)

    # ── Health & Metrics API ──────────────────────────────────────────────────

    def get_agent_health(self, agent_id: str) -> AgentHealth:
        """Return the current health of the agent."""
        return self._container.agent_manager.get_agent_health(agent_id)

    def get_agent_metrics(self, agent_id: str) -> AgentMetrics:
        """Return the current metrics of the agent."""
        return self._container.agent_manager.get_agent_metrics(agent_id)

    # ── Framework-level observability ────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Return a lightweight health summary (consistent with A2–A4 pattern)."""
        c = self._container
        return {
            "system_id":       self.SYSTEM_ID,
            "version":         self.VERSION,
            "is_running":      self._started_at is not None,
            "total_agents":    c.registry.count(),
            "active_agents":   c.registry.active_count(),
            "events_published": c.event_bus.published_count,
        }

    def status(self) -> Dict[str, Any]:
        """Return detailed status including uptime and agent counts."""
        h = self.health()
        h["started_at"] = self._started_at
        h["uptime_s"]   = (time.time() - self._started_at) if self._started_at else None
        return h

    def snapshot(self) -> AgentFrameworkSnapshot:
        """Return an immutable point-in-time snapshot of the framework."""
        return AgentFrameworkSnapshot.capture(
            registry  = self._container.registry,
            event_bus = self._container.event_bus,
        )
