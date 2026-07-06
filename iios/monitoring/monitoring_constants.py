"""
iios/monitoring/monitoring_constants.py
=========================================
Constants and enumerations for the IIOS Logging & Monitoring Framework.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Final

__all__ = [
    "LogLevel",
    "AlertLevel",
    "AlertStatus",
    "HealthStatus",
    "MetricType",
    "CheckCategory",
    "EventCategory",
    "AuditAction",
    "TraceStatus",
    "NotificationChannel",
    # Thresholds
    "CPU_WARN_PCT",
    "CPU_CRIT_PCT",
    "MEM_WARN_PCT",
    "MEM_CRIT_PCT",
    "DISK_WARN_PCT",
    "DISK_CRIT_PCT",
    "LATENCY_WARN_MS",
    "LATENCY_CRIT_MS",
    # Retention
    "DEFAULT_METRIC_RETENTION_SECONDS",
    "DEFAULT_TRACE_RETENTION_SECONDS",
    "DEFAULT_ALERT_RETENTION_SECONDS",
    "DEFAULT_HEARTBEAT_TIMEOUT_SECONDS",
    "MAX_ERROR_DEDUP_WINDOW_SECONDS",
    "MAX_METRIC_HISTORY",
    "MAX_TRACE_SPANS",
]


class LogLevel(str, Enum):
    DEBUG    = "DEBUG"
    INFO     = "INFO"
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT    = "AUDIT"       # Special level for audit records


class AlertLevel(str, Enum):
    """Severity of an alert."""
    INFO     = "INFO"
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    OPEN       = "open"
    SUPPRESSED = "suppressed"
    RESOLVED   = "resolved"
    ESCALATED  = "escalated"


class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


class MetricType(str, Enum):
    COUNTER   = "counter"    # Monotonically increasing
    GAUGE     = "gauge"      # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER     = "timer"      # Duration measurements
    RATE      = "rate"       # Events per second


class CheckCategory(str, Enum):
    """Health check category."""
    SYSTEM      = "system"
    DATABASE    = "database"
    NETWORK     = "network"
    SERVICE     = "service"
    DEPENDENCY  = "dependency"
    SECURITY    = "security"
    PERFORMANCE = "performance"
    CUSTOM      = "custom"


class EventCategory(str, Enum):
    """Business / lifecycle event categories."""
    SYSTEM      = "system"
    TRADING     = "trading"
    RISK        = "risk"
    STRATEGY    = "strategy"
    EXECUTION   = "execution"
    LEARNING    = "learning"
    CONFIG      = "config"
    SECURITY    = "security"
    LIFECYCLE   = "lifecycle"
    ALERT       = "alert"


class AuditAction(str, Enum):
    """Standard audit actions."""
    CREATE      = "CREATE"
    READ        = "READ"
    UPDATE      = "UPDATE"
    DELETE      = "DELETE"
    LOGIN       = "LOGIN"
    LOGOUT      = "LOGOUT"
    TRADE       = "TRADE"
    CONFIG      = "CONFIG"
    OVERRIDE    = "OVERRIDE"
    ALERT       = "ALERT"
    APPROVE     = "APPROVE"
    REJECT      = "REJECT"


class TraceStatus(str, Enum):
    STARTED   = "started"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class NotificationChannel(str, Enum):
    TELEGRAM  = "telegram"
    EMAIL     = "email"
    SLACK     = "slack"
    WEBHOOK   = "webhook"
    CONSOLE   = "console"
    LOG       = "log"


# ---------------------------------------------------------------------------
# Resource thresholds
# ---------------------------------------------------------------------------

CPU_WARN_PCT:  Final[float] = 75.0
CPU_CRIT_PCT:  Final[float] = 90.0
MEM_WARN_PCT:  Final[float] = 80.0
MEM_CRIT_PCT:  Final[float] = 92.0
DISK_WARN_PCT: Final[float] = 80.0
DISK_CRIT_PCT: Final[float] = 92.0

# IIOS layer latency thresholds (from system_monitor.py)
LATENCY_WARN_MS: Final[int] = 2_000
LATENCY_CRIT_MS: Final[int] = 5_000
GLOBAL_INTELLIGENCE_WARN_MS: Final[int] = 5_000
GLOBAL_INTELLIGENCE_CRIT_MS: Final[int] = 12_000

# ---------------------------------------------------------------------------
# Retention and limits
# ---------------------------------------------------------------------------

DEFAULT_METRIC_RETENTION_SECONDS:   Final[int] = 3_600   # 1 hour in memory
DEFAULT_TRACE_RETENTION_SECONDS:    Final[int] = 3_600
DEFAULT_ALERT_RETENTION_SECONDS:    Final[int] = 86_400  # 24 hours
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS:  Final[int] = 120     # 2 minutes
MAX_ERROR_DEDUP_WINDOW_SECONDS:     Final[int] = 300     # 5 minutes
MAX_METRIC_HISTORY:                 Final[int] = 10_000
MAX_TRACE_SPANS:                    Final[int] = 1_000
ALERT_COOLDOWN_SECONDS:             Final[int] = 300     # 5 min between same alert
MAX_RECENT_ALERTS:                  Final[int] = 500
MAX_ERROR_FREQUENCY_WINDOW:         Final[int] = 60      # count errors per minute

# ---------------------------------------------------------------------------
# Known IIOS layer names (for log/metric tagging)
# ---------------------------------------------------------------------------

IIOS_LAYER_NAMES: Final[tuple[str, ...]] = (
    "GlobalIntelligence",
    "MarketIntelligence",
    "MetaLearning",
    "OpportunityEngine",
    "StrategyLab",
    "CapitalRiskEngine",
    "RiskControl",
    "MarketSimulation",
    "RiskGuardian",
    "DebateAndDecision",
    "ExecutionEngine",
    "TradeMonitoring",
    "LearningSystem",
    "PerformanceAnalytics",
    "ResearchLab",
    "ValidationEngine",
    "ControlTower",
)
