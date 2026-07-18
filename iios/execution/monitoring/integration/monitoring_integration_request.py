"""iios/execution/monitoring/integration/monitoring_integration_request.py
==================================================
MonitoringIntegrationRequest — immutable request DTO for an integration
monitoring cycle.

The caller supplies pre-computed metrics (produced by the Metrics
Framework, M3) together with correlation IDs.  The integration engine
validates the request, creates a lifecycle session (M1), evaluates
alerts (M4), and returns a MonitoringIntegrationResponse.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION
from .monitoring_integration_context import MonitoringIntegrationContext


@dataclass(frozen=True)
class MonitoringIntegrationRequest:
    """
    Immutable request carrying pre-computed metrics for one integration cycle.

    Fields
    ------
    request_id:       Unique ID for this request.
    session_id:       Correlation session ID (threads through M1/M3/M4).
    portfolio_id:     Owning portfolio.
    context:          Full integration context (carries correlation IDs).
    metrics:          Dict of metric_key → pre-computed float value.
    window_metrics:   Dict of window_label → Dict[metric_key → float].
    rule_ids:         Optional subset of alert-rule IDs to evaluate.
                      Empty tuple means all registered rules.
    requested_at:     Wall-time the request was created.
    metadata:         Arbitrary caller-provided metadata.
    framework_version: Version for compatibility checks.
    """

    request_id:        str
    session_id:        str
    portfolio_id:      str
    context:           MonitoringIntegrationContext

    metrics:           Dict[str, float]              = field(default_factory=dict, compare=False)
    window_metrics:    Dict[str, Dict[str, float]]   = field(default_factory=dict, compare=False)
    rule_ids:          Tuple[str, ...]               = ()

    requested_at:      float                         = field(default_factory=time.time, compare=False)
    metadata:          Dict[str, Any]                = field(default_factory=dict, compare=False)
    framework_version: str                           = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def metric_count(self) -> int:
        return len(self.metrics)

    @property
    def has_metrics(self) -> bool:
        return bool(self.metrics)

    @property
    def has_rule_filter(self) -> bool:
        return bool(self.rule_ids)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "session_id":        self.session_id,
            "portfolio_id":      self.portfolio_id,
            "context":           self.context.to_dict(),
            "metrics":           dict(self.metrics),
            "window_metrics":    {k: dict(v) for k, v in self.window_metrics.items()},
            "rule_ids":          list(self.rule_ids),
            "requested_at":      self.requested_at,
            "metadata":          dict(self.metadata),
            "framework_version": self.framework_version,
        }


def make_monitoring_integration_request(
    session_id:   str,
    portfolio_id: str,
    context:      MonitoringIntegrationContext,
    *,
    metrics:        Optional[Dict[str, float]]            = None,
    window_metrics: Optional[Dict[str, Dict[str, float]]] = None,
    rule_ids:       Tuple[str, ...]                       = (),
    metadata:       Optional[Dict[str, Any]]              = None,
    request_id:     Optional[str]                         = None,
) -> MonitoringIntegrationRequest:
    """Factory for ``MonitoringIntegrationRequest``."""
    return MonitoringIntegrationRequest(
        request_id    = request_id or str(uuid.uuid4()),
        session_id    = session_id,
        portfolio_id  = portfolio_id,
        context       = context,
        metrics       = metrics or {},
        window_metrics= window_metrics or {},
        rule_ids      = rule_ids,
        metadata      = metadata or {},
    )
