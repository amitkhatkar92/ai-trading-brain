"""
iios/intelligence/agents/agent_manager.py
==========================================
AgentManager — lifecycle hub for all agents.

Responsibilities
----------------
- Register / unregister agents
- Initialize / shutdown all agents
- Start / stop supervision
- Expose health / stats
- Provide the agent execution interface (wraps executor)

Singleton: get_agent_manager() / reset_agent_manager()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from .agent_constants import AgentStatus, AgentType, CoordinatorStatus
from .agent_exceptions import AgentNotInitializedError, AgentNotFoundError
from .core.base_agent import BaseAgent, AgentRequest, AgentResponse
from .agent_registry import AgentRegistry, get_agent_registry
from .execution.agent_executor import AgentExecutor, get_agent_executor
from .supervision.agent_supervisor import AgentSupervisor, get_agent_supervisor
from .monitoring.agent_monitor import AgentMonitor, get_agent_monitor
from .communication.agent_router import AgentRouter, get_agent_router
from .communication.agent_mailbox import AgentMailbox

log = logging.getLogger(__name__)

__all__ = [
    "AgentManager",
    "get_agent_manager",
    "reset_agent_manager",
]


class AgentManager:
    """
    Lifecycle hub for all IIOS agents.

    Wire-up
    -------
    manager = get_agent_manager()
    manager.initialize()

    # Register an agent
    manager.register(agent, supervise=True)

    # Execute
    response = manager.execute(agent_id, request)
    """

    def __init__(
        self,
        registry:   Optional[AgentRegistry]   = None,
        executor:   Optional[AgentExecutor]   = None,
        supervisor: Optional[AgentSupervisor] = None,
        monitor:    Optional[AgentMonitor]    = None,
        router:     Optional[AgentRouter]     = None,
    ) -> None:
        self._registry   = registry   or get_agent_registry()
        self._executor   = executor   or get_agent_executor()
        self._supervisor = supervisor or get_agent_supervisor()
        self._monitor    = monitor    or get_agent_monitor()
        self._router     = router     or get_agent_router()
        self._status     = CoordinatorStatus.UNINITIALIZED
        self._lock       = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> "AgentManager":
        with self._lock:
            self._status = CoordinatorStatus.READY
        log.info("AgentManager initialized")
        return self

    def start_supervision(self) -> None:
        self._supervisor.start()

    def stop_supervision(self) -> None:
        self._supervisor.stop()

    def shutdown(self) -> None:
        with self._lock:
            self._status = CoordinatorStatus.SHUTTING_DOWN
        try:
            self._supervisor.stop()
        except Exception:
            pass
        # Shutdown all registered agents
        for agent in self._registry.all_agents():
            try:
                agent.shutdown()
            except Exception as exc:
                log.warning("Agent %r shutdown error: %s", agent.agent_id, exc)
        with self._lock:
            self._status = CoordinatorStatus.STOPPED
        log.info("AgentManager shut down")

    @property
    def is_initialized(self) -> bool:
        return self._status == CoordinatorStatus.READY

    def _require_init(self) -> None:
        if self._status not in (CoordinatorStatus.READY, CoordinatorStatus.DEGRADED):
            raise AgentNotInitializedError()

    # ── Agent management ──────────────────────────────────────────────────────

    def register(
        self,
        agent:      BaseAgent,
        supervise:  bool      = True,
        overwrite:  bool      = False,
    ) -> None:
        self._registry.register(agent, overwrite=overwrite)
        # Wire up mailbox to router
        mailbox = AgentMailbox(agent.agent_id)
        self._router.register_mailbox(agent.agent_id, mailbox)
        if supervise:
            self._supervisor.register(agent)
        log.debug("AgentManager registered agent %r", agent.agent_id)

    def unregister(self, agent_id: str) -> None:
        self._registry.unregister(agent_id)
        self._router.unregister_mailbox(agent_id)
        self._supervisor.unregister(agent_id)

    def get_agent(self, agent_id: str) -> BaseAgent:
        return self._registry.get(agent_id)

    def has_agent(self, agent_id: str) -> bool:
        return self._registry.has(agent_id)

    # ── Execution ─────────────────────────────────────────────────────────────

    def execute(
        self,
        agent_id:  str,
        request:   AgentRequest,
        timeout_s: float = 300.0,
    ) -> AgentResponse:
        """Execute a single agent by ID."""
        self._require_init()
        agent = self._registry.get(agent_id)
        result = self._executor.execute(agent, request, timeout_s=timeout_s)
        return result.response

    def execute_type(
        self,
        agent_type: AgentType,
        request:    AgentRequest,
        timeout_s:  float = 300.0,
    ) -> AgentResponse:
        """Execute the best available agent of a given type."""
        self._require_init()
        agent = self._registry.best(agent_type)
        if agent is None:
            raise AgentNotFoundError(agent_type.value)
        result = self._executor.execute(agent, request, timeout_s=timeout_s)
        return result.response

    # ── Communication ─────────────────────────────────────────────────────────

    def send_message(self, sender_id: str, recipient_id: str, payload: dict) -> None:
        self._router.send(sender_id, recipient_id, payload)

    def broadcast(self, sender_id: str, payload: dict) -> int:
        return self._router.broadcast(sender_id, payload)

    # ── Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "status":     self._status.value,
            "registry":   self._registry.stats(),
            "executor":   self._executor.stats(),
            "supervisor": self._supervisor.stats(),
            "monitor":    self._monitor.system_metrics().to_dict(),
            "router":     self._router.stats(),
        }

    def health(self) -> dict:
        return {
            "status":      self._status.value,
            "initialized": self.is_initialized,
            "agents":      self._registry.stats()["total"],
            "active":      self._registry.stats()["active"],
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_mgr_lock = threading.Lock()
_mgr_inst: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    global _mgr_inst
    if _mgr_inst is None:
        with _mgr_lock:
            if _mgr_inst is None:
                _mgr_inst = AgentManager()
    return _mgr_inst


def reset_agent_manager() -> None:
    global _mgr_inst
    with _mgr_lock:
        if _mgr_inst is not None:
            try:
                _mgr_inst.shutdown()
            except Exception:
                pass
        _mgr_inst = None
