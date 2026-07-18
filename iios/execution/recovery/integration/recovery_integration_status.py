"""
iios/execution/recovery/integration/recovery_integration_status.py
==================================================================
IntegrationStatusReport — typed report covering all component
operational statuses and current request counters.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import ComponentStatus, IntegrationStatus, VERSION


@dataclass(frozen=True)
class IntegrationStatusReport:
    """Immutable report of the integration engine's operational status."""

    report_id:          str
    captured_at:        float
    engine_status:      ComponentStatus
    policy_status:      ComponentStatus
    failover_status:    ComponentStatus
    snapshot_status:    ComponentStatus
    overall_status:     IntegrationStatus
    active_requests:    int
    processed_requests: int
    version:            str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "captured_at":        self.captured_at,
            "engine_status":      self.engine_status.value,
            "policy_status":      self.policy_status.value,
            "failover_status":    self.failover_status.value,
            "snapshot_status":    self.snapshot_status.value,
            "overall_status":     self.overall_status.value,
            "active_requests":    self.active_requests,
            "processed_requests": self.processed_requests,
            "version":            self.version,
        }


def _to_component_status(component: Any) -> ComponentStatus:
    """Map a component's lifecycle state to a ComponentStatus."""
    if component is None:
        return ComponentStatus.UNKNOWN
    try:
        state = str(component.lifecycle_state()).lower()
        if "running" in state:
            return ComponentStatus.RUNNING
        if "stopped" in state or "idle" in state:
            return ComponentStatus.STOPPED
        return ComponentStatus.UNKNOWN
    except Exception:
        return ComponentStatus.ERROR


def make_status_report(
    components:         Any,    # RecoveryComponentRegistry
    overall_status:     IntegrationStatus,
    active_requests:    int,
    processed_requests: int,
    *,
    report_id:  Optional[str]   = None,
    captured_at: Optional[float] = None,
) -> IntegrationStatusReport:
    return IntegrationStatusReport(
        report_id          = report_id or str(uuid.uuid4()),
        captured_at        = captured_at if captured_at is not None else time.time(),
        engine_status      = _to_component_status(components.engine),
        policy_status      = _to_component_status(components.policy_engine),
        failover_status    = _to_component_status(components.failover_engine),
        snapshot_status    = _to_component_status(components.snapshot_store),
        overall_status     = overall_status,
        active_requests    = active_requests,
        processed_requests = processed_requests,
    )
