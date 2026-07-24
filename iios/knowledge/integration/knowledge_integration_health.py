"""
knowledge_integration_health.py — iios.knowledge.integration
-------------------------------------------------------------
Health tracking for the Knowledge Integration system and its components.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from .constants import ComponentStatus, IntegrationState


@dataclass(frozen=True)
class ComponentHealth:
    """Health record for a single integrated component (M1–M5)."""
    component_name: str
    status:         ComponentStatus
    message:        str
    last_checked:   str

    @classmethod
    def available(cls, name: str, message: str = "OK") -> "ComponentHealth":
        return cls(
            component_name = name,
            status         = ComponentStatus.AVAILABLE,
            message        = message,
            last_checked   = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def unavailable(cls, name: str, message: str = "unavailable") -> "ComponentHealth":
        return cls(
            component_name = name,
            status         = ComponentStatus.UNAVAILABLE,
            message        = message,
            last_checked   = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def degraded(cls, name: str, message: str = "degraded") -> "ComponentHealth":
        return cls(
            component_name = name,
            status         = ComponentStatus.DEGRADED,
            message        = message,
            last_checked   = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "status":         self.status.value,
            "message":        self.message,
            "last_checked":   self.last_checked,
        }


@dataclass(frozen=True)
class KnowledgeHealthSummary:
    """
    Aggregate health of the Knowledge Integration system and all M1–M5 components.
    """
    integration_state:  IntegrationState
    overall_healthy:    bool
    component_health:   tuple   # Tuple[ComponentHealth]
    checked_at:         str
    message:            str

    @classmethod
    def healthy(
        cls,
        integration_state:  IntegrationState,
        component_health:   List[ComponentHealth],
        message:            str = "All systems healthy",
    ) -> "KnowledgeHealthSummary":
        return cls(
            integration_state = integration_state,
            overall_healthy   = True,
            component_health  = tuple(component_health),
            checked_at        = datetime.now(tz=timezone.utc).isoformat(),
            message           = message,
        )

    @classmethod
    def degraded(
        cls,
        integration_state: IntegrationState,
        component_health:  List[ComponentHealth],
        message:           str = "One or more components degraded",
    ) -> "KnowledgeHealthSummary":
        return cls(
            integration_state = integration_state,
            overall_healthy   = False,
            component_health  = tuple(component_health),
            checked_at        = datetime.now(tz=timezone.utc).isoformat(),
            message           = message,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_state": self.integration_state.value,
            "overall_healthy":   self.overall_healthy,
            "component_health":  [c.to_dict() for c in self.component_health],
            "checked_at":        self.checked_at,
            "message":           self.message,
        }


class KnowledgeIntegrationHealth:
    """
    Thread-safe health tracker for the integration system.

    Checks each registered component and returns KnowledgeHealthSummary.
    """

    def __init__(self) -> None:
        self._lock  = threading.Lock()
        self._state = IntegrationState.STOPPED

    def update_state(self, state: IntegrationState) -> None:
        with self._lock:
            self._state = state

    def check(
        self, component_statuses: List[ComponentHealth]
    ) -> KnowledgeHealthSummary:
        """Build a health summary from a list of component health checks."""
        with self._lock:
            state = self._state
        all_ok = all(
            c.status == ComponentStatus.AVAILABLE for c in component_statuses
        )
        if all_ok:
            return KnowledgeHealthSummary.healthy(state, component_statuses)
        return KnowledgeHealthSummary.degraded(
            state,
            component_statuses,
            message="One or more components unavailable or degraded",
        )
