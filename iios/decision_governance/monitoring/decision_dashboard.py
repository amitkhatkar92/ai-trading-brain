"""iios/decision_governance/monitoring/decision_dashboard.py

DecisionDashboard: in-process stats snapshot for the governance engine.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class DashboardSnapshot:
    total_submitted:  int   = 0
    approved:         int   = 0
    rejected:         int   = 0
    escalated:        int   = 0
    policy_violations: int  = 0
    alerts_raised:    int   = 0
    avg_latency_ms:   float = 0.0
    uptime_seconds:   float = 0.0
    captured_at:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "total_submitted":   self.total_submitted,
            "approved":          self.approved,
            "rejected":          self.rejected,
            "escalated":         self.escalated,
            "policy_violations": self.policy_violations,
            "alerts_raised":     self.alerts_raised,
            "avg_latency_ms":    self.avg_latency_ms,
            "uptime_seconds":    self.uptime_seconds,
            "captured_at":       self.captured_at,
        }


class DecisionDashboard:
    """Renders a point-in-time governance snapshot from a metrics dict."""

    def render(self, metrics: dict) -> DashboardSnapshot:
        return DashboardSnapshot(
            total_submitted  = metrics.get("total_submitted",  0),
            approved         = metrics.get("approved",         0),
            rejected         = metrics.get("rejected",         0),
            escalated        = metrics.get("escalated",        0),
            policy_violations= metrics.get("policy_violations",0),
            alerts_raised    = metrics.get("alerts_raised",    0),
            avg_latency_ms   = metrics.get("avg_latency_ms",   0.0),
            uptime_seconds   = metrics.get("uptime_seconds",   0.0),
        )
