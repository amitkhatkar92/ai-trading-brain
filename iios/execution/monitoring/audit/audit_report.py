"""iios/execution/monitoring/audit/audit_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.audit.audit_event import AuditEvent


@dataclass
class AuditReport:
    """Summary report produced from a set of audit events."""

    entity_id:     str             = ""
    entity_type:   str             = ""
    events:        list[AuditEvent] = field(default_factory=list)
    total_events:  int              = 0
    first_event:   float | None     = None
    last_event:    float | None     = None
    report_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at:  float            = field(default_factory=time.time)
    integrity_ok:  bool             = True
    metadata:      dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":    self.report_id,
            "entity_id":    self.entity_id,
            "entity_type":  self.entity_type,
            "total_events": self.total_events,
            "first_event":  self.first_event,
            "last_event":   self.last_event,
            "generated_at": self.generated_at,
            "integrity_ok": self.integrity_ok,
            "events":       [e.to_dict() for e in self.events],
            "metadata":     self.metadata,
        }
