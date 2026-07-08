"""
iios/intelligence/governance/audit/audit_report.py
===================================================
AuditReport — aggregated summary of audit records for a time window.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .audit_record import AuditRecord
from ..quality_constants import AuditEventType


@dataclass
class AuditReport:
    """Summary of audit activity for a product, source, or time window."""

    report_id:       str              = field(default_factory=lambda: str(uuid.uuid4()))
    product_id:      str              = "*"
    source_id:       str              = "*"
    total_entries:   int              = 0
    by_event_type:   dict[str, int]   = field(default_factory=dict)
    approvals:       int              = 0
    rejections:      int              = 0
    certifications:  int              = 0
    drift_alerts:    int              = 0
    earliest:        float            = 0.0
    latest:          float            = 0.0
    generated_at:    float            = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":      self.report_id,
            "product_id":     self.product_id,
            "source_id":      self.source_id,
            "total_entries":  self.total_entries,
            "by_event_type":  self.by_event_type,
            "approvals":      self.approvals,
            "rejections":     self.rejections,
            "certifications": self.certifications,
            "drift_alerts":   self.drift_alerts,
            "earliest":       self.earliest,
            "latest":         self.latest,
            "generated_at":   self.generated_at,
        }


def build_audit_report(
    records:    list[AuditRecord],
    product_id: str = "*",
    source_id:  str = "*",
) -> AuditReport:
    if not records:
        return AuditReport(product_id=product_id, source_id=source_id)

    by_type: dict[str, int] = {}
    for r in records:
        by_type[r.event_type.value] = by_type.get(r.event_type.value, 0) + 1

    return AuditReport(
        product_id      = product_id,
        source_id       = source_id,
        total_entries   = len(records),
        by_event_type   = by_type,
        approvals       = by_type.get(AuditEventType.APPROVAL.value, 0),
        rejections      = by_type.get(AuditEventType.REJECTION.value, 0),
        certifications  = by_type.get(AuditEventType.CERTIFICATION.value, 0),
        drift_alerts    = by_type.get(AuditEventType.DRIFT_ALERT.value, 0),
        earliest        = min(r.created_at for r in records),
        latest          = max(r.created_at for r in records),
    )
