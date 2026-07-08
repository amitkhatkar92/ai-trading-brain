"""iios/decision_governance/monitoring/governance_metrics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class GovernanceMetrics:
    """Snapshot of cumulative governance statistics."""

    total_submitted:  int   = 0
    approved:         int   = 0
    rejected:         int   = 0
    escalated:        int   = 0
    expired:          int   = 0
    certified:        int   = 0
    policy_violations: int  = 0
    alerts_raised:    int   = 0
    total_latency_ms: float = 0.0
    snapshot_at:      float = field(default_factory=time.time)

    @property
    def approval_rate(self) -> float:
        return self.approved / self.total_submitted if self.total_submitted else 0.0

    @property
    def rejection_rate(self) -> float:
        return self.rejected / self.total_submitted if self.total_submitted else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_submitted if self.total_submitted else 0.0

    def to_dict(self) -> dict:
        return {
            "total_submitted":   self.total_submitted,
            "approved":          self.approved,
            "rejected":          self.rejected,
            "escalated":         self.escalated,
            "expired":           self.expired,
            "certified":         self.certified,
            "policy_violations": self.policy_violations,
            "alerts_raised":     self.alerts_raised,
            "approval_rate":     self.approval_rate,
            "rejection_rate":    self.rejection_rate,
            "avg_latency_ms":    self.avg_latency_ms,
            "snapshot_at":       self.snapshot_at,
        }
