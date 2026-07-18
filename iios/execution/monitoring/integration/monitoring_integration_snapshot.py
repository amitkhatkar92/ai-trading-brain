"""iios/execution/monitoring/integration/monitoring_integration_snapshot.py
==================================================
MonitoringIntegrationSnapshot — immutable combined snapshot produced
after one integration monitoring cycle.

Aggregates outputs from:
  - M3 Metrics Framework (computed metric values)
  - M4 Alert Framework   (active alert summary)
  - M1 Lifecycle         (session state)

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import HealthStatus, VERSION


@dataclass(frozen=True)
class MonitoringIntegrationSnapshot:
    """
    Immutable, versioned, combined snapshot of a single integration cycle.

    Fields
    ------
    snapshot_id:              Globally unique snapshot ID.
    snapshot_version:         Monotonically increasing version per session_id.
    session_id:               Originating session.
    portfolio_id:             Owning portfolio.

    -- from M3 --
    metrics:                  Dict metric_key → float (session-wide).
    window_metrics:           Dict window → Dict metric_key → float.
    metrics_version:          Version of the underlying MetricsSnapshot.

    -- from M4 --
    active_alert_ids:         Tuple of IDs for ACTIVE/ACKNOWLEDGED/ESCALATED alerts.
    alert_counts_by_severity: Dict severity → count.
    total_active_alerts:      Total count of open alerts.
    highest_severity:         Highest alert severity string, or None.

    -- integration --
    lifecycle_state:          Final lifecycle state string.
    health_status:            Computed health at snapshot time.
    gateway_id:               Optional gateway correlation.
    strategy_id:              Optional strategy correlation.
    created_at:               Wall-time of snapshot creation.
    framework_version:        Version for compatibility checks.
    """

    snapshot_id:               str
    snapshot_version:          int
    session_id:                str
    portfolio_id:              str

    # M3 metrics
    metrics:                   Dict[str, float]              = field(default_factory=dict, compare=False)
    window_metrics:            Dict[str, Dict[str, float]]   = field(default_factory=dict, compare=False)
    metrics_version:           int                           = 0

    # M4 alerts
    active_alert_ids:          Tuple[str, ...]               = ()
    alert_counts_by_severity:  Dict[str, int]                = field(default_factory=dict, compare=False)
    total_active_alerts:       int                           = 0
    highest_severity:          Optional[str]                 = None

    # Integration
    lifecycle_state:           str                           = "stopped"
    health_status:             str                           = HealthStatus.UNKNOWN.value
    gateway_id:                Optional[str]                 = None
    strategy_id:               Optional[str]                 = None

    created_at:                float                         = field(default_factory=time.time, compare=False)
    framework_version:         str                           = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def metric_count(self) -> int:
        return len(self.metrics)

    @property
    def has_active_alerts(self) -> bool:
        return self.total_active_alerts > 0

    @property
    def has_critical_or_above(self) -> bool:
        for severity in ("critical", "emergency"):
            if self.alert_counts_by_severity.get(severity, 0) > 0:
                return True
        return False

    @property
    def is_healthy(self) -> bool:
        return self.health_status == HealthStatus.HEALTHY.value

    def get_metric(self, key: str, default: float = 0.0) -> float:
        return self.metrics.get(key, default)

    def get_window_metric(
        self, window: str, key: str, default: float = 0.0
    ) -> float:
        return self.window_metrics.get(window, {}).get(key, default)

    def is_newer_than(self, other: "MonitoringIntegrationSnapshot") -> bool:
        return self.created_at > other.created_at

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":              self.snapshot_id,
            "snapshot_version":         self.snapshot_version,
            "session_id":               self.session_id,
            "portfolio_id":             self.portfolio_id,
            "metrics":                  dict(self.metrics),
            "window_metrics":           {k: dict(v) for k, v in self.window_metrics.items()},
            "metrics_version":          self.metrics_version,
            "active_alert_ids":         list(self.active_alert_ids),
            "alert_counts_by_severity": dict(self.alert_counts_by_severity),
            "total_active_alerts":      self.total_active_alerts,
            "highest_severity":         self.highest_severity,
            "lifecycle_state":          self.lifecycle_state,
            "health_status":            self.health_status,
            "gateway_id":               self.gateway_id,
            "strategy_id":              self.strategy_id,
            "created_at":               self.created_at,
            "framework_version":        self.framework_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def make_integration_snapshot(
    session_id:    str,
    portfolio_id:  str,
    *,
    snapshot_version:         int                          = 1,
    metrics:                  Optional[Dict[str, float]]           = None,
    window_metrics:           Optional[Dict[str, Dict[str, float]]] = None,
    metrics_version:          int                          = 0,
    active_alert_ids:         Tuple[str, ...]              = (),
    alert_counts_by_severity: Optional[Dict[str, int]]     = None,
    total_active_alerts:      int                          = 0,
    highest_severity:         Optional[str]                = None,
    lifecycle_state:          str                          = "stopped",
    health_status:            str                          = HealthStatus.UNKNOWN.value,
    gateway_id:               Optional[str]                = None,
    strategy_id:              Optional[str]                = None,
    snapshot_id:              Optional[str]                = None,
) -> MonitoringIntegrationSnapshot:
    """Factory for ``MonitoringIntegrationSnapshot``."""
    return MonitoringIntegrationSnapshot(
        snapshot_id               = snapshot_id or str(uuid.uuid4()),
        snapshot_version          = snapshot_version,
        session_id                = session_id,
        portfolio_id              = portfolio_id,
        metrics                   = metrics or {},
        window_metrics            = window_metrics or {},
        metrics_version           = metrics_version,
        active_alert_ids          = active_alert_ids,
        alert_counts_by_severity  = alert_counts_by_severity or {},
        total_active_alerts       = total_active_alerts,
        highest_severity          = highest_severity,
        lifecycle_state           = lifecycle_state,
        health_status             = health_status,
        gateway_id                = gateway_id,
        strategy_id               = strategy_id,
    )
