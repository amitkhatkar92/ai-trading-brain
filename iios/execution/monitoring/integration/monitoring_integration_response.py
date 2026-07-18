"""iios/execution/monitoring/integration/monitoring_integration_response.py
==================================================
MonitoringIntegrationResponse — immutable response DTO for a completed
integration monitoring cycle.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class MonitoringIntegrationResponse:
    """
    Immutable response returned by ExecutionMonitoringIntegrationEngine.submit().

    Fields
    ------
    response_id:             Unique ID for this response.
    request_id:              ID of the originating request.
    session_id:              Session correlation ID.
    portfolio_id:            Owning portfolio.
    snapshot_id:             ID of the published IntegrationSnapshot, if any.
    metrics_count:           Number of metrics in the snapshot.
    alerts_generated:        IDs of newly generated alerts.
    alerts_suppressed:       IDs of suppressed (cooldown) alerts.
    lifecycle_state:         Final lifecycle state of the monitoring session.
    evaluation_duration_ms:  Wall-time taken for the full workflow.
    responded_at:            Wall-time of response creation.
    errors:                  Any non-fatal error messages.
    framework_version:       Version for compatibility checks.
    """

    response_id:             str
    request_id:              str
    session_id:              str
    portfolio_id:            str

    snapshot_id:             Optional[str]     = None
    metrics_count:           int               = 0
    alerts_generated:        Tuple[str, ...]   = ()
    alerts_suppressed:       Tuple[str, ...]   = ()
    lifecycle_state:         str               = "stopped"

    evaluation_duration_ms:  float             = 0.0
    responded_at:            float             = field(default_factory=time.time, compare=False)
    errors:                  Tuple[str, ...]   = ()
    framework_version:       str               = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def generated_count(self) -> int:
        return len(self.alerts_generated)

    @property
    def suppressed_count(self) -> int:
        return len(self.alerts_suppressed)

    @property
    def has_alerts(self) -> bool:
        return bool(self.alerts_generated)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def has_snapshot(self) -> bool:
        return self.snapshot_id is not None

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":            self.response_id,
            "request_id":             self.request_id,
            "session_id":             self.session_id,
            "portfolio_id":           self.portfolio_id,
            "snapshot_id":            self.snapshot_id,
            "metrics_count":          self.metrics_count,
            "alerts_generated":       list(self.alerts_generated),
            "alerts_suppressed":      list(self.alerts_suppressed),
            "lifecycle_state":        self.lifecycle_state,
            "evaluation_duration_ms": self.evaluation_duration_ms,
            "responded_at":           self.responded_at,
            "errors":                 list(self.errors),
            "framework_version":      self.framework_version,
        }


def make_monitoring_integration_response(
    request_id:   str,
    session_id:   str,
    portfolio_id: str,
    *,
    snapshot_id:            Optional[str]   = None,
    metrics_count:          int             = 0,
    alerts_generated:       Tuple[str, ...] = (),
    alerts_suppressed:      Tuple[str, ...] = (),
    lifecycle_state:        str             = "stopped",
    evaluation_duration_ms: float           = 0.0,
    errors:                 Tuple[str, ...] = (),
    response_id:            Optional[str]   = None,
) -> MonitoringIntegrationResponse:
    """Factory for ``MonitoringIntegrationResponse``."""
    return MonitoringIntegrationResponse(
        response_id            = response_id or str(uuid.uuid4()),
        request_id             = request_id,
        session_id             = session_id,
        portfolio_id           = portfolio_id,
        snapshot_id            = snapshot_id,
        metrics_count          = metrics_count,
        alerts_generated       = alerts_generated,
        alerts_suppressed      = alerts_suppressed,
        lifecycle_state        = lifecycle_state,
        evaluation_duration_ms = evaluation_duration_ms,
        errors                 = errors,
    )
