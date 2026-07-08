"""
iios/intelligence/agents/multi_agent_coordinator.py
====================================================
MultiAgentCoordinator — the mandatory gateway for all multi-agent
coordination within IIOS.

Every multi-agent interaction must flow through this coordinator.
No agent communicates directly with another agent outside this class.

Public API
----------
initialize()
register_agent(agent, supervise=True)
execute_agent(agent_id, request)
coordinate(task)                         → CoordinationResult
send_message(sender, recipient, payload)
broadcast(sender, payload)
build_consensus(decisions, method)       → ConsensusResult
stats()
health()

Singleton: get_multi_agent_coordinator() / reset_multi_agent_coordinator()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from .agent_constants import (
    AgentType, CoordinationMode, ConsensusMethod,
    CoordinatorStatus, MULTI_AGENT_ENGINE_VERSION,
)
from .agent_exceptions import AgentNotInitializedError
from .core.base_agent import BaseAgent, AgentRequest, AgentResponse, AgentDecision
from .agent_manager import AgentManager, get_agent_manager
from .agent_registry import AgentRegistry, get_agent_registry
from .agent_factory import AgentFactory, get_agent_factory
from .execution.agent_executor import AgentExecutor, get_agent_executor
from .supervision.agent_supervisor import AgentSupervisor, get_agent_supervisor
from .monitoring.agent_monitor import AgentMonitor, get_agent_monitor
from .communication.agent_router import AgentRouter, get_agent_router
from .communication.agent_channel import ChannelRegistry, get_channel_registry
from .communication.agent_event import AgentEventBus, get_agent_event_bus
from .coordination.coordination_strategy import (
    CoordinationTask, CoordinationResult, get_strategy,
)
from .consensus.consensus_engine import (
    ConsensusEngine, ConsensusResult, get_consensus_engine,
)

log = logging.getLogger(__name__)

__all__ = [
    "MultiAgentCoordinator",
    "get_multi_agent_coordinator",
    "reset_multi_agent_coordinator",
]


class MultiAgentCoordinator:
    """
    Single entry-point for all multi-agent coordination in IIOS.

    Wraps AgentManager + ConsensusEngine + coordination strategies
    and enforces the no-direct-communication rule.
    """

    def __init__(
        self,
        manager:          Optional[AgentManager]    = None,
        consensus_engine: Optional[ConsensusEngine] = None,
        factory:          Optional[AgentFactory]    = None,
    ) -> None:
        self._manager  = manager          or get_agent_manager()
        self._consensus = consensus_engine or get_consensus_engine()
        self._factory  = factory          or get_agent_factory()
        self._status   = CoordinatorStatus.UNINITIALIZED
        self._lock     = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self, start_supervision: bool = True) -> "MultiAgentCoordinator":
        with self._lock:
            self._status = CoordinatorStatus.INITIALIZING
        self._manager.initialize()
        if start_supervision:
            self._manager.start_supervision()
        with self._lock:
            self._status = CoordinatorStatus.READY
        log.info(
            "MultiAgentCoordinator v%s initialized",
            MULTI_AGENT_ENGINE_VERSION,
        )
        return self

    def shutdown(self) -> None:
        with self._lock:
            self._status = CoordinatorStatus.SHUTTING_DOWN
        self._manager.shutdown()
        with self._lock:
            self._status = CoordinatorStatus.STOPPED
        log.info("MultiAgentCoordinator shut down")

    @property
    def is_initialized(self) -> bool:
        return self._status == CoordinatorStatus.READY

    @property
    def version(self) -> str:
        return MULTI_AGENT_ENGINE_VERSION

    def _require_init(self) -> None:
        if self._status not in (CoordinatorStatus.READY, CoordinatorStatus.DEGRADED):
            raise AgentNotInitializedError()

    # ── Agent management ──────────────────────────────────────────────────────

    def register_agent(
        self,
        agent:     BaseAgent,
        supervise: bool = True,
        overwrite: bool = False,
    ) -> None:
        self._manager.register(agent, supervise=supervise, overwrite=overwrite)

    def create_agent(
        self,
        cls,
        agent_id:   str,
        name:       str             = "",
        config:     dict | None     = None,
        tags:       list[str] | None = None,
        supervise:  bool            = True,
        initialize: bool            = True,
        overwrite:  bool            = False,
    ) -> BaseAgent:
        """Create, register, and optionally supervise an agent."""
        agent = self._factory.create(
            cls        = cls,
            agent_id   = agent_id,
            name       = name,
            config     = config,
            tags       = tags,
            initialize = initialize,
            overwrite  = overwrite,
        )
        # Also wire the manager's supervision/router
        if supervise:
            self._manager._supervisor.register(agent)
            from .communication.agent_mailbox import AgentMailbox
            mailbox = AgentMailbox(agent_id)
            self._manager._router.register_mailbox(agent_id, mailbox)
        return agent

    def get_agent(self, agent_id: str) -> BaseAgent:
        return self._manager.get_agent(agent_id)

    def has_agent(self, agent_id: str) -> bool:
        return self._manager.has_agent(agent_id)

    # ── Single-agent execution ────────────────────────────────────────────────

    def execute_agent(
        self,
        agent_id:  str,
        request:   AgentRequest,
        timeout_s: float = 300.0,
    ) -> AgentResponse:
        """Execute a single registered agent. Passes through AgentManager."""
        self._require_init()
        return self._manager.execute(agent_id, request, timeout_s=timeout_s)

    def execute_by_type(
        self,
        agent_type: AgentType,
        request:    AgentRequest,
        timeout_s:  float = 300.0,
    ) -> AgentResponse:
        """Execute the best available agent of the given type."""
        self._require_init()
        return self._manager.execute_type(agent_type, request, timeout_s=timeout_s)

    # ── Multi-agent coordination ──────────────────────────────────────────────

    def coordinate(
        self,
        task: CoordinationTask,
    ) -> CoordinationResult:
        """
        Coordinate multiple agents on a task.

        The coordination mode in task.mode selects the strategy:
          SEQUENTIAL, PARALLEL, COMPETITIVE, CONSENSUS,
          HIERARCHICAL, DELEGATION, …
        """
        self._require_init()
        registry = get_agent_registry()
        agents   = {a.agent_id: a for a in registry.all_agents()}
        strategy = get_strategy(task.mode)
        t0       = time.perf_counter()
        result   = strategy.coordinate(task, agents)
        result.duration_ms = (time.perf_counter() - t0) * 1_000
        return result

    # ── Communication ─────────────────────────────────────────────────────────

    def send_message(
        self,
        sender_id:    str,
        recipient_id: str,
        payload:      dict,
    ) -> None:
        """Send a direct message from one agent to another."""
        self._require_init()
        self._manager.send_message(sender_id, recipient_id, payload)

    def broadcast(self, sender_id: str, payload: dict) -> int:
        """Broadcast a message to all registered agents."""
        self._require_init()
        return self._manager.broadcast(sender_id, payload)

    def subscribe_channel(
        self,
        channel_name: str,
        agent_id:     str,
        handler,
    ) -> None:
        """Subscribe an agent to a named channel."""
        reg = get_channel_registry()
        ch  = reg.get_or_create(channel_name)
        ch.subscribe(agent_id, handler)

    def publish_channel(self, channel_name: str, payload: dict, sender_id: str = "") -> int:
        """Publish a message to a named channel."""
        from .communication.agent_message import AgentMessage
        reg = get_channel_registry()
        ch  = reg.get_or_create(channel_name)
        msg = AgentMessage.broadcast(sender_id=sender_id, payload=payload,
                                     channel=channel_name)
        return ch.publish(msg)

    # ── Consensus ─────────────────────────────────────────────────────────────

    def build_consensus(
        self,
        decisions: list[AgentDecision],
        method:    ConsensusMethod = ConsensusMethod.CONFIDENCE_WEIGHTED,
        threshold: float           = 0.5,
        min_votes: int             = 1,
    ) -> ConsensusResult:
        """Build consensus from a list of agent decisions."""
        return self._consensus.build(
            decisions,
            method    = method,
            threshold = threshold,
            min_votes = min_votes,
        )

    # ── Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        s = self._manager.stats()
        s["coordinator_version"] = MULTI_AGENT_ENGINE_VERSION
        s["consensus"]           = self._consensus.stats()
        s["factory"]             = self._factory.stats()
        return s

    def health(self) -> dict:
        h = self._manager.health()
        h["coordinator_version"] = MULTI_AGENT_ENGINE_VERSION
        return h


# ── Singleton ─────────────────────────────────────────────────────────────────

_coord_lock = threading.Lock()
_coord_inst: Optional[MultiAgentCoordinator] = None


def get_multi_agent_coordinator() -> MultiAgentCoordinator:
    global _coord_inst
    if _coord_inst is None:
        with _coord_lock:
            if _coord_inst is None:
                _coord_inst = MultiAgentCoordinator()
    return _coord_inst


def reset_multi_agent_coordinator() -> None:
    global _coord_inst
    with _coord_lock:
        if _coord_inst is not None:
            try:
                _coord_inst.shutdown()
            except Exception:
                pass
        _coord_inst = None
