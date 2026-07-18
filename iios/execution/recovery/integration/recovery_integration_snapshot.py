"""
iios/execution/recovery/integration/recovery_integration_snapshot.py
====================================================================
IntegrationSnapshot — a point-in-time view of the integration engine's
operational state.

Different from ExecutionRecoverySnapshot (M5): this captures component
statuses, active request counts, and runtime statistics — not the outcome
of a specific recovery workflow.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationHealth, IntegrationStatus, VERSION


@dataclass(frozen=True)
class IntegrationSnapshot:
    """
    Immutable snapshot of the integration engine's operational state.

    Returned by the public status()/snapshot() API.
    """

    snapshot_id:          str
    captured_at:          float
    integration_status:   IntegrationStatus
    integration_health:   IntegrationHealth
    component_statuses:   Dict[str, str]   # component_name → status string
    active_request_count: int
    total_requests:       int
    successful_requests:  int
    failed_requests:      int
    snapshots_published:  int
    uptime_seconds:       float
    version:              str = VERSION

    @property
    def is_healthy(self) -> bool:
        return self.integration_health == IntegrationHealth.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":          self.snapshot_id,
            "captured_at":          self.captured_at,
            "integration_status":   self.integration_status.value,
            "integration_health":   self.integration_health.value,
            "component_statuses":   dict(self.component_statuses),
            "active_request_count": self.active_request_count,
            "total_requests":       self.total_requests,
            "successful_requests":  self.successful_requests,
            "failed_requests":      self.failed_requests,
            "snapshots_published":  self.snapshots_published,
            "uptime_seconds":       self.uptime_seconds,
            "version":              self.version,
        }


def make_integration_snapshot(
    integration_status:   IntegrationStatus,
    integration_health:   IntegrationHealth,
    component_statuses:   Dict[str, str],
    active_request_count: int,
    total_requests:       int,
    successful_requests:  int,
    failed_requests:      int,
    snapshots_published:  int,
    uptime_seconds:       float,
    *,
    snapshot_id:          Optional[str]   = None,
    captured_at:          Optional[float] = None,
) -> IntegrationSnapshot:
    return IntegrationSnapshot(
        snapshot_id          = snapshot_id or str(uuid.uuid4()),
        captured_at          = captured_at if captured_at is not None else time.time(),
        integration_status   = integration_status,
        integration_health   = integration_health,
        component_statuses   = dict(component_statuses),
        active_request_count = active_request_count,
        total_requests       = total_requests,
        successful_requests  = successful_requests,
        failed_requests      = failed_requests,
        snapshots_published  = snapshots_published,
        uptime_seconds       = uptime_seconds,
    )
