"""iios/execution/monitoring/monitoring_manager.py"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.execution.monitoring.alerts.alert_manager import AlertManager
from iios.execution.monitoring.alerts.alert_rule import AlertContext
from iios.execution.monitoring.alerts.notification_event import Alert
from iios.execution.monitoring.analytics.execution_analytics import ExecutionAnalytics
from iios.execution.monitoring.analytics.performance_dashboard import PerformanceDashboard
from iios.execution.monitoring.analytics.sla_monitor import SLAMonitor
from iios.execution.monitoring.audit.audit_event import AuditEvent
from iios.execution.monitoring.audit.audit_manager import AuditManager
from iios.execution.monitoring.core.execution_event import ExecutionEvent
from iios.execution.monitoring.core.execution_record import ExecutionRecord
from iios.execution.monitoring.core.execution_snapshot import ExecutionSnapshot
from iios.execution.monitoring.monitoring_constants import (
    EntityType,
    ExecutionRecordStatus,
    TERMINAL_EXECUTION_STATUSES,
)
from iios.execution.monitoring.reconciliation.reconciliation_manager import ReconciliationManager
from iios.execution.monitoring.reconciliation.reconciliation_report import ReconciliationReport
from iios.execution.monitoring.tracking.execution_metrics import ExecutionMetrics
from iios.execution.monitoring.tracking.execution_status_tracker import ExecutionStatusTracker
from iios.execution.monitoring.tracking.execution_tracker import ExecutionTracker
from iios.execution.monitoring.tracking.fill_tracker import FillRecord, FillTracker
from iios.execution.monitoring.tracking.latency_tracker import LatencyRecord, LatencyTracker


class MonitoringManager:
    """
    Orchestrates all monitoring sub-systems:

    * ExecutionTracker    — record lifecycle
    * FillTracker         — fill events
    * LatencyTracker      — per-phase latency
    * ExecutionStatusTracker — status transition log
    * ReconciliationManager
    * AuditManager
    * AlertManager
    * ExecutionAnalytics
    """

    def __init__(
        self,
        execution_tracker:  ExecutionTracker,
        fill_tracker:       FillTracker,
        latency_tracker:    LatencyTracker,
        status_tracker:     ExecutionStatusTracker,
        recon_manager:      ReconciliationManager,
        audit_manager:      AuditManager,
        alert_manager:      AlertManager,
        analytics:          ExecutionAnalytics,
        sla_monitor:        SLAMonitor | None = None,
        dashboard:          PerformanceDashboard | None = None,
    ) -> None:
        self._tracker        = execution_tracker
        self._fills          = fill_tracker
        self._latency        = latency_tracker
        self._status_tracker = status_tracker
        self._recon          = recon_manager
        self._audit          = audit_manager
        self._alerts         = alert_manager
        self._analytics      = analytics
        self._sla            = sla_monitor or SLAMonitor()
        self._dashboard      = dashboard   or PerformanceDashboard(analytics=analytics, sla_monitor=self._sla)
        self._started_at     = time.time()
        self._lock           = threading.RLock()

    # ── Execution tracking ────────────────────────────────────────────────────

    def register_execution(self, record: ExecutionRecord) -> None:
        self._tracker.create(record)

    def update_execution_status(
        self,
        execution_id: str,
        status:       ExecutionRecordStatus,
        reason:       str = "",
        source:       str = "",
    ) -> None:
        rec = self._tracker.get(execution_id)
        old = rec.status
        self._tracker.update_status(execution_id, status, reason)
        self._status_tracker.record_transition(execution_id, old, status, reason, source)

    def record_execution_event(self, event: ExecutionEvent) -> None:
        # Forward to audit log
        self._audit.record_system_event(
            action=event.event_type.value,
            data=event.to_dict(),
            source=event.source,
        )

    # ── Fill tracking ─────────────────────────────────────────────────────────

    def record_fill(self, fill: FillRecord) -> None:
        self._fills.record_fill(fill)
        self._tracker.apply_fill(fill.execution_id, fill.quantity, fill.price)

    # ── Latency tracking ──────────────────────────────────────────────────────

    def record_latency(self, record: LatencyRecord) -> None:
        self._latency.record(record)

    # ── Reconciliation ────────────────────────────────────────────────────────

    def run_reconciliation(
        self,
        internal_records:  list[dict[str, Any]],
        external_records:  list[dict[str, Any]],
        entity_type:       EntityType = EntityType.ORDER,
        id_field:          str = "order_id",
        fields_to_compare: list[str] | None = None,
    ) -> ReconciliationReport:
        return self._recon.run(
            internal_records=internal_records,
            external_records=external_records,
            entity_type=entity_type,
            id_field=id_field,
            fields_to_compare=fields_to_compare,
        )

    # ── Audit ─────────────────────────────────────────────────────────────────

    def audit(self, event: AuditEvent) -> None:
        self._audit.record(event)

    # ── Alerts ────────────────────────────────────────────────────────────────

    def check_alerts(self, context: AlertContext | None = None) -> list[Alert]:
        if context is None:
            context = AlertContext(
                execution_records=self._tracker.all_records(),
                fill_records=self._fills.all_fills(),
                latency_values_ms=list(self._latency.all_latencies()),
                reconciliation_reports=self._recon.all_reports(),
            )
        return self._alerts.check(context)

    # ── Metrics & snapshot ────────────────────────────────────────────────────

    def get_metrics(self) -> ExecutionMetrics:
        records = self._tracker.all_records()
        lat_ms  = [
            lr.latency_ms
            for lr in self._latency.all_latencies()
            if lr is not None
        ]
        return self._analytics.compute_metrics(records, lat_ms)

    def snapshot(self) -> ExecutionSnapshot:
        records   = self._tracker.all_records()
        active    = self._tracker.active_executions()
        terminal  = self._tracker.terminal_executions()
        fills     = self._fills.all_fills()
        alerts    = self._alerts.active_alerts()
        recon     = self._recon.all_reports()
        clean     = sum(1 for r in recon if r.is_clean())
        metrics   = self.get_metrics()
        return ExecutionSnapshot(
            active_executions=len(active),
            completed_executions=len([r for r in terminal if r.status == ExecutionRecordStatus.FULLY_FILLED]),
            failed_executions=len([r for r in terminal if r.status in (
                ExecutionRecordStatus.REJECTED, ExecutionRecordStatus.FAILED
            )]),
            total_fills=len(fills),
            active_alerts=len(alerts),
            uptime_sec=time.time() - self._started_at,
            metadata={
                "recon_runs":               len(recon),
                "clean_recon_runs":         clean,
                "execution_quality_index":  round(metrics.execution_quality_index, 4),
                "avg_fill_ratio":           round(metrics.avg_fill_ratio, 4),
                "avg_latency_ms":           round(metrics.avg_latency_ms, 2),
            },
        )

    def statistics(self) -> dict[str, Any]:
        return {
            "tracking":        self._tracker.statistics(),
            "fills":           self._fills.statistics(),
            "latency":         self._latency.statistics(),
            "reconciliation":  self._recon.statistics(),
            "alerts":          self._alerts.statistics(),
            "audit":           self._audit.statistics(),
            "uptime_sec":      round(time.time() - self._started_at, 1),
        }

    def generate_dashboard(self) -> dict[str, Any]:
        return self._dashboard.generate(
            records=self._tracker.all_records(),
            latency_values=list(self._latency.all_latencies()),
            recon_reports=self._recon.all_reports(),
            active_alerts=self._alerts.active_alerts(),
        )
