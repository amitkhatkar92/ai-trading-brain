"""
integration_gateway_status.py — iios.integration.gateway
----------------------------------------------------------
IntegrationGatewayStatusReport and IntegrationGatewayStatusTracker.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import (
    FRAMEWORK_VERSION,
    GATEWAY_VERSION,
    GatewayState,
)


@dataclass(frozen=True)
class IntegrationGatewayStatusReport:
    """
    Point-in-time status snapshot of the gateway.
    Returned by the public ``status()`` API.
    """
    gateway_id:       str
    gateway_state:    GatewayState
    version:          str
    framework_version: str
    active_requests:  int
    total_requests:   int
    uptime_seconds:   float
    last_request_at:  str
    component_states: Dict[str, str]   # component_type → state string
    generated_at:     str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gateway_id":        self.gateway_id,
            "gateway_state":     self.gateway_state.value,
            "version":           self.version,
            "framework_version": self.framework_version,
            "active_requests":   self.active_requests,
            "total_requests":    self.total_requests,
            "uptime_seconds":    round(self.uptime_seconds, 3),
            "last_request_at":   self.last_request_at,
            "component_states":  dict(self.component_states),
            "generated_at":      self.generated_at,
        }


class IntegrationGatewayStatusTracker:
    """
    Tracks runtime counters and state for the gateway status report.
    Thread-safe.
    """

    def __init__(self) -> None:
        self._state:            GatewayState = GatewayState.IDLE
        self._active_requests:  int          = 0
        self._total_requests:   int          = 0
        self._last_request_at:  str          = ""
        self._component_states: Dict[str, str] = {}
        self._lock              = threading.Lock()

    # ─── state management ─────────────────────────────────────────────

    def update_state(self, state: GatewayState) -> None:
        with self._lock:
            self._state = state

    # ─── request counters ─────────────────────────────────────────────

    def record_request(self, request_id: str = "") -> None:
        with self._lock:
            self._active_requests  += 1
            self._total_requests   += 1
            self._last_request_at   = datetime.now(timezone.utc).isoformat()

    def record_completion(self, request_id: str = "") -> None:
        with self._lock:
            if self._active_requests > 0:
                self._active_requests -= 1

    # ─── component state ──────────────────────────────────────────────

    def set_component_state(self, component: str, state: str) -> None:
        with self._lock:
            self._component_states[component] = state

    # ─── report ───────────────────────────────────────────────────────

    def status(
        self,
        gateway_id:     str,
        uptime_seconds: float = 0.0,
    ) -> IntegrationGatewayStatusReport:
        with self._lock:
            return IntegrationGatewayStatusReport(
                gateway_id        = gateway_id,
                gateway_state     = self._state,
                version           = GATEWAY_VERSION,
                framework_version = FRAMEWORK_VERSION,
                active_requests   = self._active_requests,
                total_requests    = self._total_requests,
                uptime_seconds    = uptime_seconds,
                last_request_at   = self._last_request_at,
                component_states  = dict(self._component_states),
                generated_at      = datetime.now(timezone.utc).isoformat(),
            )

    # ─── properties ───────────────────────────────────────────────────

    @property
    def active_requests(self) -> int:
        with self._lock:
            return self._active_requests

    @property
    def total_requests(self) -> int:
        with self._lock:
            return self._total_requests

    @property
    def current_state(self) -> GatewayState:
        with self._lock:
            return self._state
