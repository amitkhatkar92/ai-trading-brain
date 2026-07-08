"""
iios/intelligence/agents/core/base_agent.py
============================================
BaseAgent — abstract base class for every AI agent within IIOS.

Also defines the core data models shared across the agent system:
  AgentRequest   — input to any agent execution
  AgentResponse  — output from any agent execution
  AgentDecision  — a decision+confidence tuple used for consensus

Every agent type (ReasoningAgent, AnalysisAgent, DecisionAgent, etc.)
must subclass BaseAgent and implement execute().

Design rules
------------
- execute()      — synchronous, must be implemented
- async_execute() — coroutine wrapping execute() via asyncio.to_thread()
- run()           — public safe wrapper: sets status, records metrics,
                    converts exceptions to failed AgentResponse
- initialize()   — override for one-time setup (model loading, DB conn)
- shutdown()     — override for cleanup
"""

from __future__ import annotations

import time
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..agent_constants import (
    AgentType, AgentStatus, MessagePriority, SupervisionPolicy,
    HEARTBEAT_TIMEOUT_S,
)
from ..agent_exceptions import AgentStatusError

__all__ = [
    "AgentRequest",
    "AgentResponse",
    "AgentDecision",
    "BaseAgent",
]


# ══════════════════════════════════════════════════════════════════════════════
#  Data models
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentRequest:
    """
    Input to an agent execution.

    task_type   — logical name of the work item (e.g. "score_signal")
    payload     — free-form dict with task-specific data
    context     — shared execution context (symbol, date, regime, …)
    priority    — scheduling priority
    timeout_s   — maximum allowed execution time
    """
    request_id:  str           = field(default_factory=lambda: str(uuid.uuid4()))
    task_type:   str           = "generic"
    payload:     dict          = field(default_factory=dict)
    context:     dict          = field(default_factory=dict)
    priority:    MessagePriority = MessagePriority.NORMAL
    timeout_s:   float         = 300.0
    metadata:    dict          = field(default_factory=dict)
    created_at:  float         = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "task_type":  self.task_type,
            "payload":    self.payload,
            "priority":   self.priority.name,
            "timeout_s":  self.timeout_s,
            "created_at": self.created_at,
        }


@dataclass
class AgentResponse:
    """
    Output from an agent execution.

    confidence  — agent's self-reported confidence [0.0, 1.0]
    reasoning   — human-readable explanation of the decision
    """
    request_id:  str
    agent_id:    str
    success:     bool          = True
    result:      Any           = None
    error:       Optional[str] = None
    confidence:  float         = 1.0
    reasoning:   str           = ""
    duration_ms: float         = 0.0
    metadata:    dict          = field(default_factory=dict)
    created_at:  float         = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "agent_id":   self.agent_id,
            "success":    self.success,
            "result":     self.result,
            "error":      self.error,
            "confidence": round(self.confidence, 4),
            "reasoning":  self.reasoning,
            "duration_ms": round(self.duration_ms, 3),
            "created_at": self.created_at,
        }


@dataclass
class AgentDecision:
    """
    A single agent's structured decision — used by the consensus engine.

    weight      — importance multiplier for weighted voting (default 1.0)
    """
    agent_id:   str
    decision:   Any
    confidence: float          = 1.0
    reasoning:  str            = ""
    weight:     float          = 1.0
    timestamp:  float          = field(default_factory=time.time)
    metadata:   dict           = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "agent_id":   self.agent_id,
            "decision":   self.decision,
            "confidence": round(self.confidence, 4),
            "reasoning":  self.reasoning,
            "weight":     self.weight,
            "timestamp":  self.timestamp,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  BaseAgent
# ══════════════════════════════════════════════════════════════════════════════

class BaseAgent(ABC):
    """
    Abstract base for all IIOS AI agents.

    Subclass, implement execute(), optionally override initialize() /
    shutdown(), then register the instance with the AgentRegistry.
    """

    def __init__(
        self,
        agent_id:           str,
        agent_type:         AgentType,
        name:               str,
        config:             Optional[dict]       = None,
        supervision_policy: SupervisionPolicy    = SupervisionPolicy.RESTART_ON_FAILURE,
        tags:               Optional[list[str]]  = None,
        metadata:           Optional[dict]       = None,
    ) -> None:
        self.agent_id           = agent_id
        self.agent_type         = agent_type
        self.name               = name
        self.config             = config or {}
        self.supervision_policy = supervision_policy
        self._tags:    list[str] = list(tags or [])
        self._metadata: dict    = dict(metadata or {})

        self._status:           AgentStatus     = AgentStatus.REGISTERED
        self._lock:             threading.RLock = threading.RLock()
        self._last_heartbeat:   float           = time.time()
        self._execution_count:  int             = 0
        self._error_count:      int             = 0
        self._start_time:       Optional[float] = None

    # ── Abstract ──────────────────────────────────────────────────────────────

    @abstractmethod
    def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute a task. Must be implemented by every concrete agent."""
        ...

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Called once before the agent starts receiving tasks. Override for setup."""
        with self._lock:
            self._status     = AgentStatus.IDLE
            self._start_time = time.time()

    def shutdown(self) -> None:
        """Called when the agent is being decommissioned. Override for cleanup."""
        with self._lock:
            self._status = AgentStatus.STOPPED

    def pause(self) -> None:
        """Temporarily stop accepting new tasks."""
        with self._lock:
            if self._status not in (AgentStatus.IDLE, AgentStatus.RUNNING):
                raise AgentStatusError(self.agent_id, self._status.value, "pause")
            self._status = AgentStatus.PAUSED

    def resume(self) -> None:
        """Resume a paused agent."""
        with self._lock:
            if self._status != AgentStatus.PAUSED:
                raise AgentStatusError(self.agent_id, self._status.value, "resume")
            self._status = AgentStatus.IDLE

    def cancel(self) -> None:
        """Signal the agent to stop its current task at the next safe point."""
        with self._lock:
            self._status = AgentStatus.STOPPING

    def recover(self) -> None:
        """Reset error state — typically called by the supervisor after restart."""
        with self._lock:
            self._status      = AgentStatus.IDLE
            self._error_count = 0

    # ── Safe execution wrapper ─────────────────────────────────────────────────

    def run(self, request: AgentRequest) -> AgentResponse:
        """
        Thread-safe wrapper around execute().

        Manages:
          - status transitions (IDLE → RUNNING → IDLE | ERROR)
          - execution metrics (count, errors)
          - exception → AgentResponse conversion
        """
        with self._lock:
            if self._status == AgentStatus.PAUSED:
                raise AgentStatusError(self.agent_id, self._status.value, "run")
            if self._status not in (AgentStatus.IDLE, AgentStatus.RUNNING):
                # allow re-entry for agents that call run() from within execute()
                pass
            self._status = AgentStatus.RUNNING

        t0 = time.perf_counter()
        try:
            response = self.execute(request)
            response.duration_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._execution_count += 1
                self._status = AgentStatus.IDLE
            return response
        except Exception as exc:
            ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._error_count += 1
                self._status = AgentStatus.ERROR
            return AgentResponse(
                request_id  = request.request_id,
                agent_id    = self.agent_id,
                success     = False,
                error       = str(exc),
                confidence  = 0.0,
                duration_ms = ms,
            )

    async def async_execute(self, request: AgentRequest) -> AgentResponse:
        """
        Async wrapper — delegates to run() via asyncio.to_thread().

        Override for true async execution (e.g., aiohttp API calls).
        """
        import asyncio
        return await asyncio.to_thread(self.run, request)

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    def heartbeat(self) -> float:
        """Called periodically to signal the agent is alive."""
        with self._lock:
            self._last_heartbeat = time.time()
        return self._last_heartbeat

    def is_alive(self, timeout_s: float = HEARTBEAT_TIMEOUT_S) -> bool:
        return (time.time() - self._last_heartbeat) < timeout_s

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def is_ready(self) -> bool:
        return self._status in (AgentStatus.IDLE,)

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    @property
    def uptime_s(self) -> float:
        return (time.time() - self._start_time) if self._start_time else 0.0

    # ── Introspection ─────────────────────────────────────────────────────────

    def health(self) -> dict:
        return {
            "agent_id":        self.agent_id,
            "agent_type":      self.agent_type.value,
            "name":            self.name,
            "status":          self._status.value,
            "execution_count": self._execution_count,
            "error_count":     self._error_count,
            "last_heartbeat":  self._last_heartbeat,
            "uptime_s":        round(self.uptime_s, 1),
            "is_alive":        self.is_alive(),
        }

    def to_dict(self) -> dict:
        return {
            "agent_id":           self.agent_id,
            "agent_type":         self.agent_type.value,
            "name":               self.name,
            "status":             self._status.value,
            "supervision_policy": self.supervision_policy.value,
            "tags":               self._tags,
            "metadata":           self._metadata,
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"id={self.agent_id!r} "
            f"status={self._status.value}>"
        )
