"""iios/execution/gateway/integration/gateway_integration_snapshot.py
==================================================
GatewayIntegrationSnapshot — immutable point-in-time snapshot
of the full integration subsystem state.

Published by GatewayIntegrationEngine.snapshot() to allow
downstream consumers to observe subsystem health and progress
without accessing internal components.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import ComponentHealth, VERSION


@dataclass(frozen=True)
class GatewayIntegrationSnapshot:
    """
    Immutable snapshot of the integration subsystem at a moment in time.

    This is the published representation of the subsystem.  All fields
    are serialisable scalar types.  No internal objects are exposed.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    snapshot_id:    str
    integration_id: str

    # ── Component lifecycle states (string values) ────────────────────────────
    lifecycle_state:     str    # GatewayLifecycle
    engine_state:        str    # ExecutionGatewayEngine
    routing_state:       str    # RoutingEngine
    broker_layer_state:  str    # BrokerManager
    snapshot_store_state: str   # GatewaySnapshotStore

    # ── Health ────────────────────────────────────────────────────────────────
    overall_health:   ComponentHealth
    component_health: Dict[str, str]   # ComponentType.value → ComponentHealth.value

    # ── Counters ──────────────────────────────────────────────────────────────
    pending_requests:   int
    completed_requests: int
    failed_requests:    int
    total_requests:     int

    # ── Statistics ────────────────────────────────────────────────────────────
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
    def has_active_requests(self) -> bool:
        return self.pending_requests > 0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.completed_requests / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":         self.snapshot_id,
            "integration_id":      self.integration_id,
            "lifecycle_state":     self.lifecycle_state,
            "engine_state":        self.engine_state,
            "routing_state":       self.routing_state,
            "broker_layer_state":  self.broker_layer_state,
            "snapshot_store_state": self.snapshot_store_state,
            "overall_health":      self.overall_health.value,
            "component_health":    dict(self.component_health),
            "pending_requests":    self.pending_requests,
            "completed_requests":  self.completed_requests,
            "failed_requests":     self.failed_requests,
            "total_requests":      self.total_requests,
            "statistics_summary":  dict(self.statistics_summary),
            "created_at":          self.created_at,
            "version":             self.version,
            "is_healthy":          self.is_healthy,
            "success_rate":        self.success_rate,
        }
