"""audit/audit_engine.py — Audit orchestrator."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.governance.governance_constants import AuditEventType
from iios.integration.research.governance.audit.audit_history import AuditHistory, AuditRecord
from iios.integration.research.governance.audit.audit_report  import AuditReport


class AuditEngine:
    """Facade for all audit log operations."""

    def __init__(self) -> None:
        self._history = AuditHistory()

    def log_event(
        self,
        event_type:  AuditEventType,
        entity_type: str,
        entity_id:   str,
        *,
        actor:        Optional[str]  = None,
        before_state: Optional[dict] = None,
        after_state:  Optional[dict] = None,
        ip_address:   Optional[str]  = None,
        metadata:     Optional[dict] = None,
    ) -> AuditRecord:
        record = AuditRecord.create(
            event_type   = event_type,
            entity_type  = entity_type,
            entity_id    = entity_id,
            actor        = actor,
            before_state = before_state,
            after_state  = after_state,
            ip_address   = ip_address,
            metadata     = metadata,
        )
        self._history.append(record)
        return record

    def trail(
        self,
        entity_id:  str,
        *,
        event_type: Optional[AuditEventType] = None,
        limit:      int                      = 100,
    ) -> list[AuditRecord]:
        return self._history.query(entity_id=entity_id, event_type=event_type, limit=limit)

    def generate_report(
        self,
        *,
        entity_id:    Optional[str]   = None,
        period_start: Optional[float] = None,
        period_end:   Optional[float] = None,
        generated_by: Optional[str]   = None,
    ) -> AuditReport:
        return AuditReport.build(
            self._history,
            entity_id    = entity_id,
            period_start = period_start,
            period_end   = period_end,
            generated_by = generated_by,
        )

    def export(self) -> list[dict[str, Any]]:
        return self._history.export()

    def count(self) -> int:
        return self._history.count()

    def stats(self) -> dict[str, Any]:
        return {
            "total_audit_entries": self._history.count(),
        }
