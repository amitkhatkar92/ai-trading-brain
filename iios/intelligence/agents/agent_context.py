"""
iios/intelligence/agents/agent_context.py
==========================================
Thread-local execution context for the Multi-Agent Coordination Engine.

Tracks the current agent, task, and coordination context throughout
an execution chain — useful for logging, tracing, and resource governance.

Singleton: get_agent_context() / reset_agent_context()
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from .agent_constants import MessagePriority

__all__ = [
    "AgentDiagnostic",
    "AgentContext",
    "get_agent_context",
    "reset_agent_context",
    "agent_execution",
    "coordination_scope",
    "task_scope",
]


@dataclass
class AgentDiagnostic:
    """A single diagnostic entry recorded during agent execution."""
    level:      str   # "DEBUG" | "INFO" | "WARNING" | "ERROR"
    message:    str
    source:     str
    timestamp:  float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "level":     self.level,
            "message":   self.message,
            "source":    self.source,
            "timestamp": self.timestamp,
        }


class _TLS(threading.local):
    """Thread-local storage for agent context state."""

    def __init__(self) -> None:
        super().__init__()
        self._reset()

    def _reset(self) -> None:
        self.agent_id:        Optional[str]           = None
        self.task_id:         Optional[str]           = None
        self.coordination_id: Optional[str]           = None
        self.priority:        MessagePriority         = MessagePriority.NORMAL
        self.depth:           int                     = 0
        self.started_at:      float                   = time.time()
        self.diagnostics:     list[AgentDiagnostic]   = []


class AgentContext:
    """
    Thread-local context for agent execution.

    Tracks:
      - which agent is running
      - what task is being processed
      - coordination context (if part of a multi-agent task)
      - depth (for nested agent calls)
      - diagnostics (warnings / errors collected during the execution)
    """

    def __init__(self) -> None:
        self._tls = _TLS()

    # ── Read properties ───────────────────────────────────────────────────────

    @property
    def agent_id(self) -> Optional[str]:
        return self._tls.agent_id

    @property
    def task_id(self) -> Optional[str]:
        return self._tls.task_id

    @property
    def coordination_id(self) -> Optional[str]:
        return self._tls.coordination_id

    @property
    def priority(self) -> MessagePriority:
        return self._tls.priority

    @property
    def depth(self) -> int:
        return self._tls.depth

    def elapsed_ms(self) -> float:
        return (time.time() - self._tls.started_at) * 1_000

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def add_diagnostic(
        self,
        level:   str,
        message: str,
        source:  str = "",
    ) -> None:
        self._tls.diagnostics.append(
            AgentDiagnostic(level=level, message=message, source=source)
        )

    def warnings(self) -> list[AgentDiagnostic]:
        return [d for d in self._tls.diagnostics if d.level == "WARNING"]

    def errors(self) -> list[AgentDiagnostic]:
        return [d for d in self._tls.diagnostics if d.level == "ERROR"]

    def all_diagnostics(self) -> list[AgentDiagnostic]:
        return list(self._tls.diagnostics)

    # ── Context managers ──────────────────────────────────────────────────────

    @contextmanager
    def execution(
        self,
        agent_id:  Optional[str]    = None,
        priority:  MessagePriority  = MessagePriority.NORMAL,
    ):
        """Enter an agent execution context."""
        prev_agent    = self._tls.agent_id
        prev_priority = self._tls.priority
        prev_started  = self._tls.started_at
        prev_diag     = self._tls.diagnostics

        self._tls.agent_id    = agent_id
        self._tls.priority    = priority
        self._tls.started_at  = time.time()
        self._tls.diagnostics = []
        try:
            yield self
        finally:
            self._tls.agent_id    = prev_agent
            self._tls.priority    = prev_priority
            self._tls.started_at  = prev_started
            self._tls.diagnostics = prev_diag

    @contextmanager
    def coordination(self, coordination_id: str):
        """Track a multi-agent coordination context."""
        prev = self._tls.coordination_id
        self._tls.coordination_id = coordination_id
        try:
            yield self
        finally:
            self._tls.coordination_id = prev

    @contextmanager
    def task(self, task_id: str):
        """Track a task context and increment depth."""
        prev_task  = self._tls.task_id
        self._tls.task_id = task_id
        self._tls.depth  += 1
        try:
            yield self
        finally:
            self._tls.task_id  = prev_task
            self._tls.depth   -= 1


# ── Module-level context managers delegating to singleton ─────────────────────

@contextmanager
def agent_execution(
    agent_id: Optional[str]   = None,
    priority: MessagePriority = MessagePriority.NORMAL,
):
    """Module-level CM — delegates to the singleton AgentContext."""
    with get_agent_context().execution(agent_id=agent_id, priority=priority):
        yield


@contextmanager
def coordination_scope(coordination_id: str):
    with get_agent_context().coordination(coordination_id):
        yield


@contextmanager
def task_scope(task_id: str):
    with get_agent_context().task(task_id):
        yield


# ── Singleton ─────────────────────────────────────────────────────────────────

_ctx_lock = threading.Lock()
_ctx_inst: Optional[AgentContext] = None


def get_agent_context() -> AgentContext:
    global _ctx_inst
    if _ctx_inst is None:
        with _ctx_lock:
            if _ctx_inst is None:
                _ctx_inst = AgentContext()
    return _ctx_inst


def reset_agent_context() -> None:
    global _ctx_inst
    with _ctx_lock:
        _ctx_inst = None
