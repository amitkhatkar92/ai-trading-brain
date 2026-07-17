"""iios/execution/gateway/integration/gateway_integration_response.py
==================================================
GatewayIntegrationResponse — immutable result of a completed
gateway integration workflow.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationOutcome, IntegrationRequestStatus, VERSION


@dataclass(frozen=True)
class GatewayIntegrationResponse:
    """
    Immutable response returned by GatewayIntegrationManager.execute().

    Published to all registered event listeners and stored in
    GatewayIntegrationRegistry.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    response_id:    str
    request_id:     str
    integration_id: str

    # ── Outcome ───────────────────────────────────────────────────────────────
    status:  IntegrationRequestStatus
    outcome: IntegrationOutcome

    # ── Correlation ───────────────────────────────────────────────────────────
    execution_id:         str
    order_id:             str
    portfolio_id:         str
    strategy_id:          str
    gateway_snapshot_id:  Optional[str]
    routing_decision_id:  Optional[str]
    selected_broker_id:   Optional[str]
    selected_broker_name: Optional[str]

    # ── Error (empty on success) ──────────────────────────────────────────────
    failure_reason: Optional[str]

    # ── Timing ────────────────────────────────────────────────────────────────
    processing_duration_ms: float

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: float = field(default_factory=time.time, compare=False)

    # ── Framework ─────────────────────────────────────────────────────────────
    version: str = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_success(self) -> bool:
        return self.outcome == IntegrationOutcome.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status == IntegrationRequestStatus.FAILED

    @property
    def is_routed(self) -> bool:
        return self.selected_broker_id is not None

    @property
    def has_snapshot(self) -> bool:
        return self.gateway_snapshot_id is not None

    @property
    def has_failure(self) -> bool:
        return bool(self.failure_reason)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":             self.response_id,
            "request_id":              self.request_id,
            "integration_id":          self.integration_id,
            "status":                  self.status.value,
            "outcome":                 self.outcome.value,
            "execution_id":            self.execution_id,
            "order_id":                self.order_id,
            "portfolio_id":            self.portfolio_id,
            "strategy_id":             self.strategy_id,
            "gateway_snapshot_id":     self.gateway_snapshot_id,
            "routing_decision_id":     self.routing_decision_id,
            "selected_broker_id":      self.selected_broker_id,
            "selected_broker_name":    self.selected_broker_name,
            "failure_reason":          self.failure_reason,
            "processing_duration_ms":  self.processing_duration_ms,
            "created_at":              self.created_at,
            "version":                 self.version,
            # derived
            "is_success":  self.is_success,
            "is_failed":   self.is_failed,
            "is_routed":   self.is_routed,
            "has_snapshot": self.has_snapshot,
        }
