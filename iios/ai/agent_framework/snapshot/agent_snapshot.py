"""
agent_snapshot.py -- iios.ai.agent_framework.snapshot
=======================================================
:class:`AgentSnapshot`          — point-in-time snapshot of one agent.
:class:`AgentFrameworkSnapshot` — point-in-time snapshot of the whole framework.

Immutable.  Used by dashboards, audit logs, and health monitors.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, FrozenSet

if TYPE_CHECKING:
    from ..events.agent_event_bus import AgentEventBus
    from ..registry.agent_registry import AgentRegistry


@dataclass(frozen=True)
class AgentSnapshot:
    """Point-in-time state of one registered agent."""

    agent_id:        str
    agent_name:      str
    agent_type:      str
    is_active:       bool
    is_shutdown:     bool
    health_status:   str
    tasks_assigned:  int
    tasks_completed: int
    tasks_failed:    int
    avg_exec_ms:     float
    captured_at:     float

    @property
    def taken_at(self) -> float:  # pragma: no cover  # deprecated alias
        """Deprecated: use captured_at."""
        return self.captured_at


@dataclass(frozen=True)
class AgentFrameworkSnapshot:
    """
    Aggregate point-in-time snapshot of the entire A5 framework.

    Captured via :meth:`capture` from the live registry and event bus.
    """

    snapshot_id:          str
    captured_at:          float
    total_agents:         int
    active_agents:        int
    total_tasks_completed: int
    total_tasks_failed:   int
    events_published:     int
    agent_snapshots:      FrozenSet[AgentSnapshot]

    @property
    def taken_at(self) -> float:  # pragma: no cover  # deprecated alias
        """Deprecated: use captured_at."""
        return self.captured_at

    @classmethod
    def capture(
        cls,
        registry:  "AgentRegistry",
        event_bus: "AgentEventBus",
    ) -> "AgentFrameworkSnapshot":
        """Build a snapshot from the live registry and event bus state."""
        agent_snaps = []
        total_completed = 0
        total_failed    = 0
        active_count    = 0

        with registry._lock:
            agents = list(registry._agents.values())

        for agent in agents:
            m = agent.metrics
            h = agent.health
            snap = AgentSnapshot(
                agent_id        = agent.agent_id,
                agent_name      = agent.agent_name,
                agent_type      = agent.agent_type,
                is_active       = agent.is_active,
                is_shutdown     = agent.is_shutdown,
                health_status   = h.status.value,
                tasks_assigned  = m.tasks_assigned,
                tasks_completed = m.tasks_completed,
                tasks_failed    = m.tasks_failed,
                avg_exec_ms     = m.avg_execution_ms,
                captured_at     = time.time(),
            )
            agent_snaps.append(snap)
            total_completed += m.tasks_completed
            total_failed    += m.tasks_failed
            if agent.is_active:
                active_count += 1

        return cls(
            snapshot_id           = str(uuid.uuid4()),
            captured_at           = time.time(),
            total_agents          = len(agents),
            active_agents         = active_count,
            total_tasks_completed = total_completed,
            total_tasks_failed    = total_failed,
            events_published      = event_bus.published_count,
            agent_snapshots       = frozenset(agent_snaps),
        )
