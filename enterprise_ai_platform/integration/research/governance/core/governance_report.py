"""core/governance_report.py — Governance summary report entity."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GovernanceReport:
    """
    Point-in-time snapshot of the governance engine state.

    Generated on demand by the ResearchGovernanceEngine.stats() / generate_report().
    """
    report_id:     str
    generated_at:  float
    engine_status: str
    uptime_sec:    float
    total_projects:    int
    active_projects:   int
    total_artifacts:   int
    total_approvals:   int
    pending_approvals: int
    total_audit_entries: int
    compliance_summary: dict[str, int]
    lineage_nodes:     int
    provenance_records: int
    performance:       dict[str, Any]
    metadata:          dict[str, Any]

    @classmethod
    def create(
        cls,
        engine_status: str,
        uptime_sec:    float,
        *,
        report_id:     Optional[str] = None,
        **kwargs: Any,
    ) -> "GovernanceReport":
        return cls(
            report_id          = report_id or f"gr_{uuid.uuid4().hex[:10]}",
            generated_at       = time.time(),
            engine_status      = engine_status,
            uptime_sec         = uptime_sec,
            total_projects     = kwargs.get("total_projects", 0),
            active_projects    = kwargs.get("active_projects", 0),
            total_artifacts    = kwargs.get("total_artifacts", 0),
            total_approvals    = kwargs.get("total_approvals", 0),
            pending_approvals  = kwargs.get("pending_approvals", 0),
            total_audit_entries = kwargs.get("total_audit_entries", 0),
            compliance_summary = kwargs.get("compliance_summary", {}),
            lineage_nodes      = kwargs.get("lineage_nodes", 0),
            provenance_records = kwargs.get("provenance_records", 0),
            performance        = kwargs.get("performance", {}),
            metadata           = kwargs.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "generated_at":       self.generated_at,
            "engine_status":      self.engine_status,
            "uptime_sec":         self.uptime_sec,
            "total_projects":     self.total_projects,
            "active_projects":    self.active_projects,
            "total_artifacts":    self.total_artifacts,
            "total_approvals":    self.total_approvals,
            "pending_approvals":  self.pending_approvals,
            "total_audit_entries": self.total_audit_entries,
            "compliance_summary": self.compliance_summary,
            "lineage_nodes":      self.lineage_nodes,
            "provenance_records": self.provenance_records,
            "performance":        self.performance,
        }
