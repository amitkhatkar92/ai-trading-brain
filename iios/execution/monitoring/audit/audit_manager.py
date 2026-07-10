"""iios/execution/monitoring/audit/audit_manager.py"""
from __future__ import annotations

import logging
from typing import Any

from iios.execution.monitoring.monitoring_constants import AuditEventType
from iios.execution.monitoring.audit.audit_event import AuditEvent
from iios.execution.monitoring.audit.audit_history import AuditHistory
from iios.execution.monitoring.audit.audit_registry import AuditRegistry
from iios.execution.monitoring.audit.audit_report import AuditReport

logger = logging.getLogger(__name__)


class AuditManager:
    """
    High-level interface for recording and querying audit events.

    Wraps AuditRegistry and provides convenience factories for common
    audit event types.
    """

    def __init__(self, registry: AuditRegistry | None = None) -> None:
        self._registry = registry or AuditRegistry()

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(self, event: AuditEvent) -> None:
        self._registry.record(event)
        logger.debug(
            "Audit: %s %s/%s",
            event.event_type.value, event.entity_type, event.entity_id,
        )

    def record_order_submitted(
        self,
        order_id:  str,
        broker_id: str,
        payload:   dict[str, Any],
        source:    str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=AuditEventType.ORDER_SUBMITTED,
            entity_type="order",
            entity_id=order_id,
            broker_id=broker_id,
            action="submit",
            after_state=payload,
            source=source,
        )
        self.record(event)
        return event

    def record_order_filled(
        self,
        order_id:    str,
        broker_id:   str,
        fill_data:   dict[str, Any],
        source:      str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=AuditEventType.ORDER_FILLED,
            entity_type="order",
            entity_id=order_id,
            broker_id=broker_id,
            action="fill",
            after_state=fill_data,
            source=source,
        )
        self.record(event)
        return event

    def record_execution_started(
        self,
        execution_id: str,
        data:         dict[str, Any],
        source:       str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_STARTED,
            entity_type="execution",
            entity_id=execution_id,
            action="start",
            after_state=data,
            source=source,
        )
        self.record(event)
        return event

    def record_discrepancy(
        self,
        entity_id:  str,
        entity_type: str,
        details:    dict[str, Any],
        source:     str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=AuditEventType.DISCREPANCY_DETECTED,
            entity_type=entity_type,
            entity_id=entity_id,
            action="discrepancy",
            after_state=details,
            source=source,
        )
        self.record(event)
        return event

    def record_system_event(
        self,
        action: str,
        data:   dict[str, Any] = {},
        source: str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_EVENT,
            entity_type="system",
            entity_id="system",
            action=action,
            after_state=data,
            source=source,
        )
        self.record(event)
        return event

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_trail(self, entity_id: str) -> list[AuditEvent]:
        return self._registry.for_entity(entity_id)

    def generate_report(self, entity_id: str, entity_type: str = "") -> AuditReport:
        events = self._registry.for_entity(entity_id)
        tampered_ids = set()
        for e in events:
            if not e.verify_integrity():
                tampered_ids.add(e.event_id)
        report = AuditReport(
            entity_id=entity_id,
            entity_type=entity_type,
            events=events,
            total_events=len(events),
            first_event=events[0].timestamp if events else None,
            last_event=events[-1].timestamp if events else None,
            integrity_ok=len(tampered_ids) == 0,
        )
        return report

    def statistics(self) -> dict[str, Any]:
        return self._registry.statistics()
