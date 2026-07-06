"""
iios.monitoring
================
IIOS Logging & Monitoring Framework — Wave 2.

Provides structured logging, metrics, health checks, distributed tracing,
alerting, notifications, and diagnostics for all 17 IIOS pipeline layers.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

__version__ = "0.2.0"
__status__ = "implemented"
__wave__ = 2

# --- Exceptions ---
from .monitoring_exceptions import (
    MonitoringError,
    LoggingError,
    MetricError,
    HealthCheckError,
    AlertError,
    TraceError,
    DiagnosticError,
    HeartbeatError,
    NotificationError,
    AuditError,
    EventLogError,
    RegistryError,
)

# --- Constants & Enums ---
from .monitoring_constants import (
    LogLevel,
    AlertLevel,
    AlertStatus,
    HealthStatus,
    MetricType,
    CheckCategory,
    EventCategory,
    AuditAction,
    TraceStatus,
    NotificationChannel,
    CPU_WARN_PCT,
    CPU_CRIT_PCT,
    MEM_WARN_PCT,
    MEM_CRIT_PCT,
    DISK_WARN_PCT,
    DISK_CRIT_PCT,
    LATENCY_WARN_MS,
    LATENCY_CRIT_MS,
    GLOBAL_INTELLIGENCE_WARN_MS,
    GLOBAL_INTELLIGENCE_CRIT_MS,
    DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    ALERT_COOLDOWN_SECONDS,
    MAX_RECENT_ALERTS,
    IIOS_LAYER_NAMES,
)

# --- Models ---
from .monitoring_models import (
    LogRecord,
    AuditRecord,
    EventRecord,
    PerformanceRecord,
    ErrorRecord,
    MetricPoint,
    MetricSeries,
    TraceSpan,
    TraceContext,
    HealthCheckResult,
    SystemHealthReport,
    AlertEvent,
    HeartbeatRecord,
    DiagnosticSnapshot,
    NotificationRecord,
    MonitoringContext,
)

# --- Logger factory ---
from .logger_factory import (
    LoggerFactory,
    IIOSLogger,
    get_logger,
    reset_factory,
)

# --- Structured logger ---
from .structured_logger import (
    StructuredLogger,
    get_structured_logger,
    correlation_context,
    set_context,
    get_context,
    clear_context,
)

# --- Audit logger ---
from .audit_logger import (
    AuditLogger,
    get_audit_logger,
)

# --- Event logger ---
from .event_logger import (
    EventLogger,
    get_event_logger,
)

# --- Performance logger ---
from .performance_logger import (
    PerformanceLogger,
    get_performance_logger,
)

# --- Error logger ---
from .error_logger import (
    ErrorLogger,
    get_error_logger,
)

# --- Trace manager ---
from .trace_manager import (
    TraceManager,
    get_trace_manager,
    current_trace,
    current_span,
)

# --- Metrics manager ---
from .metrics_manager import (
    MetricsManager,
    get_metrics_manager,
)

# --- Health checker ---
from .health_checker import (
    HealthCheck,
    LambdaHealthCheck,
    CallableHealthCheck,
    CPUHealthCheck,
    MemoryHealthCheck,
    DiskHealthCheck,
    DatabaseHealthCheck,
    ThreadPoolHealthCheck,
    ImportHealthCheck,
)

# --- Health manager ---
from .health_manager import (
    HealthManager,
    get_health_manager,
)

# --- Heartbeat manager ---
from .heartbeat_manager import (
    HeartbeatManager,
    get_heartbeat_manager,
)

# --- Diagnostic manager ---
from .diagnostic_manager import (
    DiagnosticManager,
    get_diagnostic_manager,
)

# --- Alert manager ---
from .alert_manager import (
    AlertManager,
    get_alert_manager,
)

# --- Notification manager ---
from .notification_manager import (
    NotificationManager,
    ConsoleChannel,
    LogChannel,
    TelegramChannel,
    WebhookChannel,
    get_notification_manager,
)

# --- Logging manager ---
from .logging_manager import (
    LoggingManager,
    get_logging_manager,
)

# --- Registry ---
from .monitoring_registry import (
    MonitoringRegistry,
    get_monitoring_registry,
)

__all__ = [
    # Exceptions
    "MonitoringError", "LoggingError", "MetricError", "HealthCheckError",
    "AlertError", "TraceError", "DiagnosticError", "HeartbeatError",
    "NotificationError", "AuditError", "EventLogError", "RegistryError",
    # Enums / Constants
    "LogLevel", "AlertLevel", "AlertStatus", "HealthStatus", "MetricType",
    "CheckCategory", "EventCategory", "AuditAction", "TraceStatus",
    "NotificationChannel",
    "CPU_WARN_PCT", "CPU_CRIT_PCT", "MEM_WARN_PCT", "MEM_CRIT_PCT",
    "DISK_WARN_PCT", "DISK_CRIT_PCT", "LATENCY_WARN_MS", "LATENCY_CRIT_MS",
    "GLOBAL_INTELLIGENCE_WARN_MS", "GLOBAL_INTELLIGENCE_CRIT_MS",
    "DEFAULT_HEARTBEAT_TIMEOUT_SECONDS", "ALERT_COOLDOWN_SECONDS",
    "MAX_RECENT_ALERTS", "IIOS_LAYER_NAMES",
    # Models
    "LogRecord", "AuditRecord", "EventRecord", "PerformanceRecord",
    "ErrorRecord", "MetricPoint", "MetricSeries", "TraceSpan", "TraceContext",
    "HealthCheckResult", "SystemHealthReport", "AlertEvent", "HeartbeatRecord",
    "DiagnosticSnapshot", "NotificationRecord", "MonitoringContext",
    # Loggers
    "LoggerFactory", "IIOSLogger", "get_logger", "reset_factory",
    "StructuredLogger", "get_structured_logger",
    "correlation_context", "set_context", "get_context", "clear_context",
    "AuditLogger", "get_audit_logger",
    "EventLogger", "get_event_logger",
    "PerformanceLogger", "get_performance_logger",
    "ErrorLogger", "get_error_logger",
    # Managers
    "TraceManager", "get_trace_manager", "current_trace", "current_span",
    "MetricsManager", "get_metrics_manager",
    "HealthCheck", "LambdaHealthCheck", "CallableHealthCheck",
    "CPUHealthCheck", "MemoryHealthCheck", "DiskHealthCheck",
    "DatabaseHealthCheck", "ThreadPoolHealthCheck", "ImportHealthCheck",
    "HealthManager", "get_health_manager",
    "HeartbeatManager", "get_heartbeat_manager",
    "DiagnosticManager", "get_diagnostic_manager",
    "AlertManager", "get_alert_manager",
    "NotificationManager", "ConsoleChannel", "LogChannel",
    "TelegramChannel", "WebhookChannel", "get_notification_manager",
    "LoggingManager", "get_logging_manager",
    "MonitoringRegistry", "get_monitoring_registry",
]

