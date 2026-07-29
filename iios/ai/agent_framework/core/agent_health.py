"""
agent_health.py -- iios.ai.agent_framework.core
================================================
:class:`HealthStatus` — agent health states.
:class:`AgentHealth`  — immutable agent health report.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, Tuple


class HealthStatus(str, Enum):
    """Agent health states in ascending order of concern."""

    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"

    def is_ok(self) -> bool:
        """Return True for HEALTHY or DEGRADED (agent still usable)."""
        return self in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


@dataclass(frozen=True)
class AgentHealth:
    """
    Point-in-time health snapshot for one agent.

    Immutable — updated health is represented by creating a new instance
    via one of the factory class methods.
    """

    agent_id:   str
    status:     HealthStatus
    checked_at: float
    message:    str
    details:    FrozenSet[Tuple[str, Any]]

    # ── Factories ────────────────────────────────────────────────────────────

    @classmethod
    def healthy(
        cls,
        agent_id: str,
        message:  str = "OK",
        **details: Any,
    ) -> "AgentHealth":
        return cls(
            agent_id   = agent_id,
            status     = HealthStatus.HEALTHY,
            checked_at = time.time(),
            message    = message,
            details    = frozenset(details.items()),
        )

    @classmethod
    def degraded(
        cls,
        agent_id: str,
        message:  str,
        **details: Any,
    ) -> "AgentHealth":
        return cls(
            agent_id   = agent_id,
            status     = HealthStatus.DEGRADED,
            checked_at = time.time(),
            message    = message,
            details    = frozenset(details.items()),
        )

    @classmethod
    def unhealthy(
        cls,
        agent_id: str,
        message:  str,
        **details: Any,
    ) -> "AgentHealth":
        return cls(
            agent_id   = agent_id,
            status     = HealthStatus.UNHEALTHY,
            checked_at = time.time(),
            message    = message,
            details    = frozenset(details.items()),
        )

    @classmethod
    def unknown(cls, agent_id: str) -> "AgentHealth":
        return cls(
            agent_id   = agent_id,
            status     = HealthStatus.UNKNOWN,
            checked_at = time.time(),
            message    = "Health state unknown",
            details    = frozenset(),
        )

    # ── Accessors ─────────────────────────────────────────────────────────────

    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def is_usable(self) -> bool:
        """HEALTHY or DEGRADED — agent can still accept tasks."""
        return self.status.is_ok()

    def details_as_dict(self) -> Dict[str, Any]:
        return dict(self.details)
