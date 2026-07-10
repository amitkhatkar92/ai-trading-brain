"""audit/audit_report.py — Audit summary report generation."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.audit.audit_history import AuditHistory, AuditRecord
from iios.integration.research.governance.governance_constants import AuditEventType


@dataclass
class AuditReport:
    """
    Summary audit report covering a time range and optional entity filter.
    """
    report_id:     str
    entity_id:     Optional[str]
    period_start:  Optional[float]
    period_end:    Optional[float]
    total_events:  int
    by_event_type: dict[str, int]
    by_actor:      dict[str, int]
    sample:        list[dict[str, Any]]   # first N records in range
    generated_at:  float
    generated_by:  Optional[str]

    @classmethod
    def build(
        cls,
        history:       AuditHistory,
        *,
        entity_id:    Optional[str]   = None,
        period_start: Optional[float] = None,
        period_end:   Optional[float] = None,
        sample_size:  int             = 20,
        generated_by: Optional[str]   = None,
    ) -> "AuditReport":
        records = history.query(entity_id=entity_id, limit=100_000)
        if period_start is not None:
            records = [r for r in records if r.occurred_at >= period_start]
        if period_end is not None:
            records = [r for r in records if r.occurred_at <= period_end]

        by_event: dict[str, int] = {}
        by_actor: dict[str, int] = {}
        for r in records:
            k = r.event_type.value
            by_event[k] = by_event.get(k, 0) + 1
            ak = r.actor or "unknown"
            by_actor[ak] = by_actor.get(ak, 0) + 1

        return cls(
            report_id    = f"arpt_{uuid.uuid4().hex[:10]}",
            entity_id    = entity_id,
            period_start = period_start,
            period_end   = period_end,
            total_events = len(records),
            by_event_type = by_event,
            by_actor     = by_actor,
            sample       = [r.to_dict() for r in records[:sample_size]],
            generated_at = time.time(),
            generated_by = generated_by,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":     self.report_id,
            "entity_id":     self.entity_id,
            "period_start":  self.period_start,
            "period_end":    self.period_end,
            "total_events":  self.total_events,
            "by_event_type": self.by_event_type,
            "by_actor":      self.by_actor,
            "sample_count":  len(self.sample),
            "generated_at":  self.generated_at,
            "generated_by":  self.generated_by,
        }
