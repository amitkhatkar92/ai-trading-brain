"""iios/execution/gateway/integration/gateway_integration_status.py
==================================================
GatewayIntegrationStatus — immutable point-in-time status
of the integration engine.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import ComponentHealth, VERSION


@dataclass(frozen=True)
class GatewayIntegrationStatus:
    """
    Immutable status summary returned by
    GatewayIntegrationEngine.status().

    Provides a lightweight alternative to the full
    GatewayIntegrationSnapshot.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    integration_id: str

    # ── State ─────────────────────────────────────────────────────────────────
    lifecycle_state: str        # EngineState.value
    is_running:      bool
    is_initialized:  bool

    # ── Components ────────────────────────────────────────────────────────────
    component_count:         int
    healthy_component_count: int
    overall_health:          ComponentHealth

    # ── Request tracking ──────────────────────────────────────────────────────
    pending_requests:   int
    completed_requests: int
    failed_requests:    int

    # ── Summary ───────────────────────────────────────────────────────────────
    statistics_summary: Dict[str, Any] = field(
        default_factory=dict, compare=False
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: float = field(default_factory=time.time, compare=False)

    # ── Framework ─────────────────────────────────────────────────────────────
    version: str = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_healthy(self) -> bool:
        return self.overall_health == ComponentHealth.HEALTHY

    @property
    def all_components_healthy(self) -> bool:
        return self.component_count > 0 and (
            self.healthy_component_count == self.component_count
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_id":         self.integration_id,
            "lifecycle_state":        self.lifecycle_state,
            "is_running":             self.is_running,
            "is_initialized":         self.is_initialized,
            "component_count":        self.component_count,
            "healthy_component_count": self.healthy_component_count,
            "overall_health":         self.overall_health.value,
            "pending_requests":       self.pending_requests,
            "completed_requests":     self.completed_requests,
            "failed_requests":        self.failed_requests,
            "statistics_summary":     dict(self.statistics_summary),
            "created_at":             self.created_at,
            "version":                self.version,
            "is_healthy":             self.is_healthy,
            "all_components_healthy": self.all_components_healthy,
        }
