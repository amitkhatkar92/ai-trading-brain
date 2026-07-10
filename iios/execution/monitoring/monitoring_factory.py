"""iios/execution/monitoring/monitoring_factory.py"""
from __future__ import annotations

from iios.execution.monitoring.alerts.alert_engine import AlertEngine
from iios.execution.monitoring.alerts.alert_manager import AlertManager
from iios.execution.monitoring.analytics.execution_analytics import ExecutionAnalytics
from iios.execution.monitoring.analytics.performance_dashboard import PerformanceDashboard
from iios.execution.monitoring.analytics.sla_monitor import SLAMonitor
from iios.execution.monitoring.audit.audit_manager import AuditManager
from iios.execution.monitoring.audit.audit_registry import AuditRegistry
from iios.execution.monitoring.audit.execution_audit_engine import ExecutionAuditEngine
from iios.execution.monitoring.reconciliation.discrepancy_detector import DiscrepancyDetector
from iios.execution.monitoring.reconciliation.reconciliation_engine import ReconciliationEngine
from iios.execution.monitoring.reconciliation.reconciliation_manager import ReconciliationManager
from iios.execution.monitoring.tracking.execution_status_tracker import ExecutionStatusTracker
from iios.execution.monitoring.tracking.execution_tracker import ExecutionTracker
from iios.execution.monitoring.tracking.fill_tracker import FillTracker
from iios.execution.monitoring.tracking.latency_tracker import LatencyTracker


class MonitoringFactory:
    """
    Creates fully-wired monitoring subsystem instances.

    Decouples object construction from the engines that use them.
    """

    @staticmethod
    def create_execution_tracker(**kw) -> ExecutionTracker:
        return ExecutionTracker(**kw)

    @staticmethod
    def create_fill_tracker(**kw) -> FillTracker:
        return FillTracker(**kw)

    @staticmethod
    def create_latency_tracker(**kw) -> LatencyTracker:
        return LatencyTracker(**kw)

    @staticmethod
    def create_status_tracker() -> ExecutionStatusTracker:
        return ExecutionStatusTracker()

    @staticmethod
    def create_reconciliation_manager(**kw) -> ReconciliationManager:
        detector = DiscrepancyDetector()
        engine   = ReconciliationEngine(detector=detector)
        return ReconciliationManager(engine=engine, **kw)

    @staticmethod
    def create_audit_manager(**kw) -> AuditManager:
        return AuditManager(**kw)

    @staticmethod
    def create_alert_manager(load_defaults: bool = True, **kw) -> AlertManager:
        return AlertManager(load_defaults=load_defaults, **kw)

    @staticmethod
    def create_analytics() -> ExecutionAnalytics:
        return ExecutionAnalytics()

    @staticmethod
    def create_sla_monitor(**kw) -> SLAMonitor:
        return SLAMonitor(**kw)

    @staticmethod
    def create_dashboard(**kw) -> PerformanceDashboard:
        return PerformanceDashboard(**kw)
