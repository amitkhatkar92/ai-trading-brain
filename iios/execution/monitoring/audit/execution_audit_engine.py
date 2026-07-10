"""iios/execution/monitoring/audit/execution_audit_engine.py

Facade that ties AuditManager to the execution lifecycle.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.monitoring.audit.audit_event import AuditEvent
from iios.execution.monitoring.audit.audit_manager import AuditManager
from iios.execution.monitoring.audit.audit_registry import AuditRegistry
from iios.execution.monitoring.core.execution_record import ExecutionRecord


class ExecutionAuditEngine:
    """
    Generates audit events from execution lifecycle changes.

    Call the appropriate method whenever an execution state changes;
    the engine creates and stores an AuditEvent automatically.
    """

    def __init__(self, audit_manager: AuditManager | None = None) -> None:
        self._audit = audit_manager or AuditManager()
        self._lock  = threading.RLock()

    @property
    def manager(self) -> AuditManager:
        return self._audit

    def on_execution_started(self, record: ExecutionRecord) -> AuditEvent:
        return self._audit.record_execution_started(
            execution_id=record.execution_id,
            data=record.to_dict(),
            source="ExecutionAuditEngine",
        )

    def on_order_submitted(self, record: ExecutionRecord) -> AuditEvent:
        return self._audit.record_order_submitted(
            order_id=record.order_id,
            broker_id=record.broker_id,
            payload=record.to_dict(),
            source="ExecutionAuditEngine",
        )

    def on_fill_received(
        self,
        order_id:  str,
        broker_id: str,
        fill_data: dict[str, Any],
    ) -> AuditEvent:
        return self._audit.record_order_filled(
            order_id=order_id,
            broker_id=broker_id,
            fill_data=fill_data,
            source="ExecutionAuditEngine",
        )

    def get_trail(self, entity_id: str) -> list[AuditEvent]:
        return self._audit.get_trail(entity_id)

    def statistics(self) -> dict[str, Any]:
        return self._audit.statistics()
