"""
iios/intelligence/agents/monitoring/agent_monitor.py
=====================================================
AgentMonitor — collects runtime metrics for all agents.

Tracks:
  - execution counts per agent
  - success / failure rates
  - latency histograms (min, max, avg)
  - uptime
  - system-level aggregates

Singleton: get_agent_monitor() / reset_agent_monitor()
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from ..core.base_agent import AgentResponse

__all__ = [
    "AgentMetrics",
    "SystemMetrics",
    "AgentMonitor",
    "get_agent_monitor",
    "reset_agent_monitor",
]


@dataclass
class AgentMetrics:
    """Per-agent runtime metrics."""
    agent_id:        str
    execution_count: int    = 0
    success_count:   int    = 0
    failure_count:   int    = 0
    total_ms:        float  = 0.0
    min_ms:          float  = float("inf")
    max_ms:          float  = 0.0
    first_seen_at:   float  = field(default_factory=time.time)
    last_seen_at:    float  = field(default_factory=time.time)

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.execution_count if self.execution_count else 0.0

    @property
    def success_rate(self) -> float:
        return self.success_count / self.execution_count if self.execution_count else 0.0

    def record(self, response: AgentResponse) -> None:
        self.execution_count += 1
        self.last_seen_at     = time.time()
        if response.success:
            self.success_count += 1
        else:
            self.failure_count += 1
        ms = response.duration_ms
        self.total_ms += ms
        self.min_ms    = min(self.min_ms, ms)
        self.max_ms    = max(self.max_ms, ms)

    def to_dict(self) -> dict:
        return {
            "agent_id":        self.agent_id,
            "execution_count": self.execution_count,
            "success_count":   self.success_count,
            "failure_count":   self.failure_count,
            "success_rate":    round(self.success_rate, 4),
            "avg_ms":          round(self.avg_ms,     3),
            "min_ms":          round(self.min_ms,     3) if self.min_ms != float("inf") else 0.0,
            "max_ms":          round(self.max_ms,     3),
        }


@dataclass
class SystemMetrics:
    """Aggregate metrics across all agents."""
    total_executions:  int   = 0
    total_successes:   int   = 0
    total_failures:    int   = 0
    total_ms:          float = 0.0
    started_at:        float = field(default_factory=time.time)

    @property
    def uptime_s(self) -> float:
        return time.time() - self.started_at

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.total_executions if self.total_executions else 0.0

    @property
    def success_rate(self) -> float:
        return (
            self.total_successes / self.total_executions
            if self.total_executions else 0.0
        )

    def to_dict(self) -> dict:
        return {
            "total_executions": self.total_executions,
            "total_successes":  self.total_successes,
            "total_failures":   self.total_failures,
            "success_rate":     round(self.success_rate, 4),
            "avg_ms":           round(self.avg_ms,       3),
            "uptime_s":         round(self.uptime_s,     1),
        }


class AgentMonitor:
    """
    Collects and serves runtime metrics for the multi-agent system.
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._agents: dict[str, AgentMetrics] = {}
        self._system  = SystemMetrics()

    def record(self, response: AgentResponse) -> None:
        """Record the result of an agent execution."""
        with self._lock:
            if response.agent_id not in self._agents:
                self._agents[response.agent_id] = AgentMetrics(
                    agent_id=response.agent_id
                )
            self._agents[response.agent_id].record(response)
            self._system.total_executions += 1
            self._system.total_ms         += response.duration_ms
            if response.success:
                self._system.total_successes += 1
            else:
                self._system.total_failures += 1

    def get_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        with self._lock:
            return self._agents.get(agent_id)

    def all_agent_metrics(self) -> dict[str, AgentMetrics]:
        with self._lock:
            return dict(self._agents)

    def system_metrics(self) -> SystemMetrics:
        with self._lock:
            return self._system

    def top_agents(
        self,
        n:   int    = 5,
        by:  str    = "execution_count",
    ) -> list[AgentMetrics]:
        with self._lock:
            metrics = list(self._agents.values())
        reverse = by not in ("avg_ms", "failure_count")
        return sorted(metrics, key=lambda m: getattr(m, by, 0), reverse=reverse)[:n]

    def stats(self) -> dict:
        with self._lock:
            return {
                "system":  self._system.to_dict(),
                "agents":  {k: v.to_dict() for k, v in self._agents.items()},
            }

    def clear(self) -> None:
        with self._lock:
            self._agents.clear()
            self._system = SystemMetrics()


# ── Singleton ─────────────────────────────────────────────────────────────────

_mon_lock = threading.Lock()
_mon_inst: Optional[AgentMonitor] = None


def get_agent_monitor() -> AgentMonitor:
    global _mon_inst
    if _mon_inst is None:
        with _mon_lock:
            if _mon_inst is None:
                _mon_inst = AgentMonitor()
    return _mon_inst


def reset_agent_monitor() -> None:
    global _mon_inst
    with _mon_lock:
        _mon_inst = None
