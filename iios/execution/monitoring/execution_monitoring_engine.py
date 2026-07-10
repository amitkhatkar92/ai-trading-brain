"""iios/execution/monitoring/execution_monitoring_engine.py"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from iios.execution.monitoring.alerts.alert_rule import AlertContext
from iios.execution.monitoring.alerts.notification_event import Alert
from iios.execution.monitoring.audit.audit_event import AuditEvent
from iios.execution.monitoring.core.execution_event import ExecutionEvent
from iios.execution.monitoring.core.execution_record import ExecutionRecord
from iios.execution.monitoring.core.execution_snapshot import ExecutionSnapshot
from iios.execution.monitoring.monitoring_constants import (
    MONITORING_ENGINE_SYSTEM_ID,
    MONITORING_ENGINE_VERSION,
    MonitoringStatus,
)
from iios.execution.monitoring.monitoring_exceptions import (
    MonitoringEngineAlreadyRunningError,
    MonitoringEngineNotInitializedError,
)
from iios.execution.monitoring.monitoring_factory import MonitoringFactory
from iios.execution.monitoring.monitoring_manager import MonitoringManager
from iios.execution.monitoring.reconciliation.reconciliation_report import ReconciliationReport
from iios.execution.monitoring.tracking.execution_metrics import ExecutionMetrics
from iios.execution.monitoring.tracking.fill_tracker import FillRecord
from iios.execution.monitoring.tracking.latency_tracker import LatencyRecord

logger = logging.getLogger(__name__)


class ExecutionMonitoringEngine:
    """
    Top-level facade for the Execution Monitoring, Reconciliation & Audit subsystem.

    Singleton lifecycle managed by *get_execution_monitoring_engine()* /
    *reset_execution_monitoring_engine()*.
    """

    def __init__(self, manager: MonitoringManager) -> None:
        self._manager     = manager
        self._status      = MonitoringStatus.STOPPED
        self._started_at: float | None = None
        self._lock        = threading.RLock()
        logger.info(
            "ExecutionMonitoringEngine v%s initialised (%s)",
            MONITORING_ENGINE_VERSION,
            MONITORING_ENGINE_SYSTEM_ID,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            if self._status == MonitoringStatus.ACTIVE:
                raise MonitoringEngineAlreadyRunningError(
                    "ExecutionMonitoringEngine is already running", "EM-061"
                )
            self._status     = MonitoringStatus.ACTIVE
            self._started_at = time.time()
        logger.info("ExecutionMonitoringEngine started")

    def stop(self) -> None:
        with self._lock:
            self._status = MonitoringStatus.STOPPED
        logger.info("ExecutionMonitoringEngine stopped")

    @property
    def status(self) -> MonitoringStatus:
        return self._status

    def is_running(self) -> bool:
        return self._status == MonitoringStatus.ACTIVE

    def _assert_running(self) -> None:
        if self._status != MonitoringStatus.ACTIVE:
            raise MonitoringEngineNotInitializedError(
                "ExecutionMonitoringEngine is not running", "EM-060"
            )

    # ── Execution tracking ────────────────────────────────────────────────────

    def register_execution(self, record: ExecutionRecord) -> None:
        self._assert_running()
        self._manager.register_execution(record)

    def record_execution_event(self, event: ExecutionEvent) -> None:
        self._assert_running()
        self._manager.record_execution_event(event)

    def record_fill(self, fill: FillRecord) -> None:
        self._assert_running()
        self._manager.record_fill(fill)

    def record_latency(self, latency: LatencyRecord) -> None:
        self._assert_running()
        self._manager.record_latency(latency)

    # ── Reconciliation ────────────────────────────────────────────────────────

    def run_reconciliation(
        self,
        internal_records:  list[dict[str, Any]],
        external_records:  list[dict[str, Any]],
        entity_type_str:   str  = "ORDER",
        id_field:          str  = "order_id",
        fields_to_compare: list[str] | None = None,
    ) -> ReconciliationReport:
        self._assert_running()
        from iios.execution.monitoring.monitoring_constants import EntityType
        entity_type = EntityType(entity_type_str.lower())
        return self._manager.run_reconciliation(
            internal_records=internal_records,
            external_records=external_records,
            entity_type=entity_type,
            id_field=id_field,
            fields_to_compare=fields_to_compare,
        )

    # ── Audit ─────────────────────────────────────────────────────────────────

    def audit_event(self, event: AuditEvent) -> None:
        self._assert_running()
        self._manager.audit(event)

    # ── Alerts ────────────────────────────────────────────────────────────────

    def check_alerts(self, context: AlertContext | None = None) -> list[Alert]:
        self._assert_running()
        return self._manager.check_alerts(context)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_metrics(self) -> ExecutionMetrics:
        self._assert_running()
        return self._manager.get_metrics()

    def get_snapshot(self) -> ExecutionSnapshot:
        self._assert_running()
        return self._manager.snapshot()

    def summary(self) -> dict[str, Any]:
        stats = self._manager.statistics()
        stats.update({
            "version":    MONITORING_ENGINE_VERSION,
            "system_id":  MONITORING_ENGINE_SYSTEM_ID,
            "status":     self._status.value,
            "started_at": self._started_at,
        })
        return stats


# ── Singleton ────────────────────────────────────────────────────────────────

_engine_instance: ExecutionMonitoringEngine | None = None
_engine_lock = threading.Lock()


def get_execution_monitoring_engine(
    auto_start: bool = False,
) -> ExecutionMonitoringEngine:
    """
    Return (or create) the module-level singleton.

    If *auto_start* is True, the engine is started on first creation.
    """
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                factory = MonitoringFactory
                manager = MonitoringManager(
                    execution_tracker=factory.create_execution_tracker(),
                    fill_tracker=factory.create_fill_tracker(),
                    latency_tracker=factory.create_latency_tracker(),
                    status_tracker=factory.create_status_tracker(),
                    recon_manager=factory.create_reconciliation_manager(),
                    audit_manager=factory.create_audit_manager(),
                    alert_manager=factory.create_alert_manager(),
                    analytics=factory.create_analytics(),
                    sla_monitor=factory.create_sla_monitor(),
                    dashboard=factory.create_dashboard(),
                )
                _engine_instance = ExecutionMonitoringEngine(manager)
                if auto_start:
                    _engine_instance.start()
    return _engine_instance


def reset_execution_monitoring_engine() -> None:
    """Reset singleton — primarily for tests."""
    global _engine_instance
    with _engine_lock:
        if _engine_instance is not None and _engine_instance.is_running():
            _engine_instance.stop()
        _engine_instance = None
