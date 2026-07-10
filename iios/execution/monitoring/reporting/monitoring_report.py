"""iios/execution/monitoring/reporting/monitoring_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MonitoringReport:
    """Snapshot report of the execution monitoring engine state."""

    report_id:        str             = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at:     float           = field(default_factory=time.time)
    session_id:       str             = ""
    execution_metrics: dict[str, Any] = field(default_factory=dict)
    reconciliation:   dict[str, Any]  = field(default_factory=dict)
    sla:              dict[str, Any]  = field(default_factory=dict)
    alerts:           dict[str, Any]  = field(default_factory=dict)
    audit_stats:      dict[str, Any]  = field(default_factory=dict)
    metadata:         dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":         self.report_id,
            "generated_at":      self.generated_at,
            "session_id":        self.session_id,
            "execution_metrics": self.execution_metrics,
            "reconciliation":    self.reconciliation,
            "sla":               self.sla,
            "alerts":            self.alerts,
            "audit_stats":       self.audit_stats,
            "metadata":          self.metadata,
        }
