"""
integration_gateway_health.py — iios.integration.gateway
----------------------------------------------------------
IntegrationGatewayHealth — tracks and reports health of the gateway
and all integrated subsystem components.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from .constants import GatewayComponentType, GatewayState


# ════════════════════════════════════════════════════════════════════════
# Data objects
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GatewayComponentHealth:
    """Health snapshot for a single integrated subsystem component."""
    component_type: GatewayComponentType
    status:         str           # "healthy" | "degraded" | "unavailable" | "unknown"
    message:        str
    checked_at:     str

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"

    @property
    def is_degraded(self) -> bool:
        return self.status == "degraded"

    @property
    def is_unavailable(self) -> bool:
        return self.status == "unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_type": self.component_type.value,
            "status":         self.status,
            "message":        self.message,
            "checked_at":     self.checked_at,
        }


@dataclass(frozen=True)
class IntegrationHealthSummary:
    """
    Aggregated health summary for the gateway and all its components.
    Returned by the public ``health()`` API.
    """
    gateway_id:      str
    gateway_state:   GatewayState
    overall_health:  str     # "healthy" | "degraded" | "unavailable"
    components:      Dict[str, GatewayComponentHealth]   # component_type.value → health
    active_requests: int
    uptime_seconds:  float
    generated_at:    str

    @property
    def is_healthy(self) -> bool:
        return self.overall_health == "healthy"

    @property
    def is_degraded(self) -> bool:
        return self.overall_health == "degraded"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gateway_id":      self.gateway_id,
            "gateway_state":   self.gateway_state.value,
            "overall_health":  self.overall_health,
            "components":      {k: v.to_dict() for k, v in self.components.items()},
            "active_requests": self.active_requests,
            "uptime_seconds":  self.uptime_seconds,
            "generated_at":    self.generated_at,
        }


# ════════════════════════════════════════════════════════════════════════
# Health monitor
# ════════════════════════════════════════════════════════════════════════


class IntegrationGatewayHealth:
    """
    Tracks and evaluates health for the gateway and its 5 components.

    Thread-safe.  The gateway calls *record_component* whenever
    a subsystem check completes, then calls *check* to produce
    an IntegrationHealthSummary for the public health() API.
    """

    _HEALTHY    = "healthy"
    _DEGRADED   = "degraded"
    _UNAVAILABLE = "unavailable"
    _UNKNOWN    = "unknown"

    def __init__(self, max_history: int = 200) -> None:
        self._components: Dict[GatewayComponentType, GatewayComponentHealth] = {}
        self._history:    Deque[IntegrationHealthSummary] = deque(maxlen=max_history)
        self._lock        = threading.Lock()

    # ─── component recording ──────────────────────────────────────────

    def record_component(
        self,
        component_type: GatewayComponentType,
        status:         str,
        message:        str = "",
    ) -> None:
        """Record the health status for *component_type*."""
        entry = GatewayComponentHealth(
            component_type = component_type,
            status         = status,
            message        = message,
            checked_at     = datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._components[component_type] = entry

    def mark_healthy(self, component_type: GatewayComponentType, message: str = "") -> None:
        self.record_component(component_type, self._HEALTHY, message)

    def mark_degraded(self, component_type: GatewayComponentType, message: str = "") -> None:
        self.record_component(component_type, self._DEGRADED, message)

    def mark_unavailable(self, component_type: GatewayComponentType, message: str = "") -> None:
        self.record_component(component_type, self._UNAVAILABLE, message)

    # ─── check ────────────────────────────────────────────────────────

    def check(
        self,
        gateway_id:      str,
        gateway_state:   GatewayState,
        active_requests: int  = 0,
        uptime_seconds:  float = 0.0,
    ) -> IntegrationHealthSummary:
        """
        Produce an IntegrationHealthSummary from the current component
        health records.  The summary is stored in internal history.
        """
        with self._lock:
            components_snapshot = dict(self._components)

        # Derive overall health
        statuses = {h.status for h in components_snapshot.values()}
        if gateway_state not in (GatewayState.ACTIVE, GatewayState.IDLE):
            overall = self._UNAVAILABLE
        elif self._UNAVAILABLE in statuses:
            overall = self._DEGRADED
        elif self._DEGRADED in statuses:
            overall = self._DEGRADED
        else:
            overall = self._HEALTHY

        # Build keyed dict (str keys for JSON compatibility)
        comp_dict = {k.value: v for k, v in components_snapshot.items()}

        summary = IntegrationHealthSummary(
            gateway_id      = gateway_id,
            gateway_state   = gateway_state,
            overall_health  = overall,
            components      = comp_dict,
            active_requests = active_requests,
            uptime_seconds  = uptime_seconds,
            generated_at    = datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._history.append(summary)
        return summary

    # ─── history ──────────────────────────────────────────────────────

    def latest(self) -> Optional[IntegrationHealthSummary]:
        """Return the most recently generated health summary."""
        with self._lock:
            return self._history[-1] if self._history else None

    def history(self, n: Optional[int] = None) -> List[IntegrationHealthSummary]:
        with self._lock:
            items = list(self._history)
        return items[-n:] if n is not None else items

    def clear_history(self) -> int:
        with self._lock:
            n = len(self._history)
            self._history.clear()
            return n
