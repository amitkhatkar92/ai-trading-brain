"""enterprise_ai_platform/execution/monitoring/__init__.py

Execution Monitoring, Reconciliation & Audit Engine.
"""
from __future__ import annotations

from enterprise_ai_platform.execution.monitoring.alerts import (
    Alert,
    AlertContext,
    AlertEngine,
    AlertManager,
    AlertRule,
    HighLatencyRule,
)
from enterprise_ai_platform.execution.monitoring.analytics import (
    ExecutionAnalytics,
    PerformanceDashboard,
    QualityMetrics,
    SLAMonitor,
)
from enterprise_ai_platform.execution.monitoring.audit import (
    AuditEvent,
    AuditHistory,
    AuditManager,
    AuditRegistry,
    AuditReport,
    ExecutionAuditEngine,
)
from enterprise_ai_platform.execution.monitoring.core import (
    ExecutionEvent,
    ExecutionRecord,
    ExecutionSnapshot,
    MonitoringSession,
)
from enterprise_ai_platform.execution.monitoring.execution_monitoring_engine import (
    ExecutionMonitoringEngine,
    get_execution_monitoring_engine,
    reset_execution_monitoring_engine,
)
from enterprise_ai_platform.execution.monitoring.history import ExecutionHistory
from enterprise_ai_platform.execution.monitoring.monitoring_constants import (
    AlertSeverity,
    AlertStatus,
    AuditEventType,
    DiscrepancyType,
    EntityType,
    ExecutionEventType,
    ExecutionRecordStatus,
    FillType,
    LatencyPhase,
    MonitoringStatus,
    ReconciliationStatus,
    SLAStatus,
    TERMINAL_EXECUTION_STATUSES,
)
from enterprise_ai_platform.execution.monitoring.monitoring_context import (
    MonitoringContextState,
    monitoring_operation_context,
)
from enterprise_ai_platform.execution.monitoring.monitoring_exceptions import (
    AlertError,
    AlertRuleNotFoundError,
    AlertStorageOverflowError,
    AuditError,
    AuditEventNotFoundError,
    AuditStorageOverflowError,
    AuditTamperingDetectedError,
    ExecutionRecordAlreadyExistsError,
    ExecutionRecordNotFoundError,
    ExecutionTrackingError,
    ExecutionTrackerOverflowError,
    MonitoringEngineAlreadyRunningError,
    MonitoringEngineError,
    MonitoringEngineNotInitializedError,
    MonitoringRegistryError,
    ReconciliationError,
    ReconciliationFailedError,
    ReconciliationNotFoundError,
)
from enterprise_ai_platform.execution.monitoring.monitoring_factory import MonitoringFactory
from enterprise_ai_platform.execution.monitoring.monitoring_manager import MonitoringManager
from enterprise_ai_platform.execution.monitoring.monitoring_registry import (
    MonitoringRegistry,
    get_monitoring_registry,
    reset_monitoring_registry,
)
from enterprise_ai_platform.execution.monitoring.reconciliation import (
    DiscrepancyDetector,
    ReconciliationEngine,
    ReconciliationManager,
    ReconciliationReport,
    ReconciliationResult,
)
from enterprise_ai_platform.execution.monitoring.reporting import MonitoringReport
from enterprise_ai_platform.execution.monitoring.tracking import (
    ExecutionMetrics,
    ExecutionStatusTracker,
    ExecutionTracker,
    FillRecord,
    FillTracker,
    LatencyRecord,
    LatencyTracker,
)

__version__ = "1.0.0"

__all__ = [
    # Engine
    "ExecutionMonitoringEngine",
    "get_execution_monitoring_engine",
    "reset_execution_monitoring_engine",
    # Manager / Factory / Registry / Context
    "MonitoringManager",
    "MonitoringFactory",
    "MonitoringRegistry",
    "get_monitoring_registry",
    "reset_monitoring_registry",
    "MonitoringContextState",
    "monitoring_operation_context",
    # Tracking
    "ExecutionTracker",
    "FillTracker",
    "FillRecord",
    "LatencyTracker",
    "LatencyRecord",
    "ExecutionStatusTracker",
    "ExecutionMetrics",
    # Core models
    "ExecutionRecord",
    "ExecutionEvent",
    "ExecutionSnapshot",
    "MonitoringSession",
    # Reconciliation
    "ReconciliationEngine",
    "ReconciliationManager",
    "ReconciliationReport",
    "ReconciliationResult",
    "DiscrepancyDetector",
    # Audit
    "AuditEvent",
    "AuditHistory",
    "AuditManager",
    "AuditRegistry",
    "AuditReport",
    "ExecutionAuditEngine",
    # Alerts
    "Alert",
    "AlertContext",
    "AlertEngine",
    "AlertManager",
    "AlertRule",
    "ExceptionHandler",
    "HighLatencyRule",
    "HighRejectionRateRule",
    "MissingFillRule",
    "OrderRejectedRule",
    "ReconciliationDiscrepancyRule",
    # Analytics
    "ExecutionAnalytics",
    "PerformanceDashboard",
    "QualityMetrics",
    "SLAMonitor",
    # History & Reporting
    "ExecutionHistory",
    "MonitoringReport",
    # Enums & constants
    "AlertSeverity",
    "AlertStatus",
    "AuditEventType",
    "DiscrepancyType",
    "EntityType",
    "ExecutionEventType",
    "ExecutionRecordStatus",
    "FillType",
    "LatencyPhase",
    "MonitoringStatus",
    "ReconciliationStatus",
    "SLAStatus",
    "TERMINAL_EXECUTION_STATUSES",
    # Exceptions
    "MonitoringEngineError",
    "ExecutionTrackingError",
    "ExecutionRecordNotFoundError",
    "ExecutionRecordAlreadyExistsError",
    "ExecutionTrackerOverflowError",
    "ReconciliationError",
    "ReconciliationFailedError",
    "ReconciliationNotFoundError",
    "AuditError",
    "AuditEventNotFoundError",
    "AuditStorageOverflowError",
    "AuditTamperingDetectedError",
    "AlertError",
    "AlertRuleNotFoundError",
    "AlertStorageOverflowError",
    "MonitoringRegistryError",
    "MonitoringEngineNotInitializedError",
    "MonitoringEngineAlreadyRunningError",
]
