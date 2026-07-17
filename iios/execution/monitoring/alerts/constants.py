"""iios/execution/monitoring/alerts/constants.py
==================================================
Constants, enumerations, and configuration for the IIOS
Execution Alert Framework.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID   = "iios:execution:monitoring:alerts:engine"
MANAGER_SYSTEM_ID  = "iios:execution:monitoring:alerts:manager"
REGISTRY_SYSTEM_ID = "iios:execution:monitoring:alerts:registry"
FACTORY_SYSTEM_ID  = "iios:execution:monitoring:alerts:factory"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_ALERTS       = 10_000
DEFAULT_MAX_HISTORY      = 1_000
DEFAULT_COOLDOWN_SECONDS = 60.0
DEFAULT_EXPIRY_SECONDS   = 3_600.0   # 1 hour
DEFAULT_MAX_ESCALATIONS  = 3


# ── Alert severity (ascending order) ─────────────────────────────────────────

class AlertSeverity(str, Enum):
    INFO      = "info"
    NOTICE    = "notice"
    WARNING   = "warning"
    HIGH      = "high"
    CRITICAL  = "critical"
    EMERGENCY = "emergency"


SEVERITY_WEIGHT: dict = {
    AlertSeverity.INFO:      1,
    AlertSeverity.NOTICE:    2,
    AlertSeverity.WARNING:   3,
    AlertSeverity.HIGH:      4,
    AlertSeverity.CRITICAL:  5,
    AlertSeverity.EMERGENCY: 6,
}


# ── Alert categories ──────────────────────────────────────────────────────────

class AlertCategory(str, Enum):
    EXECUTION_PERFORMANCE = "execution_performance"
    GATEWAY               = "gateway"
    BROKER                = "broker"
    QUEUE                 = "queue"
    LATENCY               = "latency"
    AVAILABILITY          = "availability"
    RELIABILITY           = "reliability"
    RISK                  = "risk"
    OPERATIONAL           = "operational"
    INFRASTRUCTURE        = "infrastructure"


# ── Alert types ───────────────────────────────────────────────────────────────

class AlertType(str, Enum):
    HIGH_LATENCY               = "high_latency"
    QUEUE_CONGESTION           = "queue_congestion"
    EXECUTION_FAILURE_RATE     = "execution_failure_rate"
    BROKER_UNAVAILABLE         = "broker_unavailable"
    GATEWAY_DEGRADED           = "gateway_degraded"
    RETRY_THRESHOLD_EXCEEDED   = "retry_threshold_exceeded"
    TIMEOUT_THRESHOLD_EXCEEDED = "timeout_threshold_exceeded"
    MONITORING_FAILURE         = "monitoring_failure"
    RESOURCE_EXHAUSTION        = "resource_exhaustion"
    SUBSYSTEM_UNHEALTHY        = "subsystem_unhealthy"


# ── Alert status ──────────────────────────────────────────────────────────────

class AlertStatus(str, Enum):
    ACTIVE       = "active"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED    = "escalated"
    RESOLVED     = "resolved"
    EXPIRED      = "expired"
    SUPPRESSED   = "suppressed"


# ── Alert policy types ────────────────────────────────────────────────────────

class AlertPolicyType(str, Enum):
    IMMEDIATE           = "immediate"
    CONSECUTIVE_FAILURE = "consecutive_failure"
    ROLLING_WINDOW      = "rolling_window"
    RATE_THRESHOLD      = "rate_threshold"
    DURATION_THRESHOLD  = "duration_threshold"
    COMPOSITE           = "composite"
    CUSTOM              = "custom"


# ── Threshold operators ───────────────────────────────────────────────────────

class ThresholdOperator(str, Enum):
    GT  = "gt"   # >
    GTE = "gte"  # >=
    LT  = "lt"   # <
    LTE = "lte"  # <=
    EQ  = "eq"   # ==
    NEQ = "neq"  # !=


# ── Alert event types ─────────────────────────────────────────────────────────

class AlertEventType(str, Enum):
    ALERT_GENERATED    = "alert_generated"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_ESCALATED    = "alert_escalated"
    ALERT_RESOLVED     = "alert_resolved"
    ALERT_EXPIRED      = "alert_expired"
    ALERT_SUPPRESSED   = "alert_suppressed"


# ── Default latency thresholds (ms) ──────────────────────────────────────────

DEFAULT_LATENCY_WARNING_MS   = 500.0
DEFAULT_LATENCY_CRITICAL_MS  = 1_000.0
DEFAULT_LATENCY_EMERGENCY_MS = 5_000.0

# ── Default rate thresholds [0, 1] ───────────────────────────────────────────

DEFAULT_FAILURE_RATE_WARNING   = 0.05
DEFAULT_FAILURE_RATE_CRITICAL  = 0.10
DEFAULT_FAILURE_RATE_EMERGENCY = 0.20

DEFAULT_RETRY_RATE_WARNING    = 0.10
DEFAULT_RETRY_RATE_CRITICAL   = 0.20

DEFAULT_TIMEOUT_RATE_WARNING  = 0.05
DEFAULT_TIMEOUT_RATE_CRITICAL = 0.10

# ── Queue thresholds (ms) ─────────────────────────────────────────────────────

DEFAULT_QUEUE_WAIT_WARNING_MS  = 200.0
DEFAULT_QUEUE_WAIT_CRITICAL_MS = 1_000.0

# ── Broker / gateway thresholds ───────────────────────────────────────────────

DEFAULT_BROKER_UTIL_CRITICAL   = 0.95
DEFAULT_GATEWAY_THROUGHPUT_MIN = 0.10   # fraction below this = degraded

# ── Alert type → Category mapping ─────────────────────────────────────────────

ALERT_TYPE_CATEGORY: dict = {
    AlertType.HIGH_LATENCY:               AlertCategory.LATENCY,
    AlertType.QUEUE_CONGESTION:           AlertCategory.QUEUE,
    AlertType.EXECUTION_FAILURE_RATE:     AlertCategory.EXECUTION_PERFORMANCE,
    AlertType.BROKER_UNAVAILABLE:         AlertCategory.BROKER,
    AlertType.GATEWAY_DEGRADED:           AlertCategory.GATEWAY,
    AlertType.RETRY_THRESHOLD_EXCEEDED:   AlertCategory.RELIABILITY,
    AlertType.TIMEOUT_THRESHOLD_EXCEEDED: AlertCategory.RELIABILITY,
    AlertType.MONITORING_FAILURE:         AlertCategory.OPERATIONAL,
    AlertType.RESOURCE_EXHAUSTION:        AlertCategory.INFRASTRUCTURE,
    AlertType.SUBSYSTEM_UNHEALTHY:        AlertCategory.AVAILABILITY,
}

# ── Status sets ───────────────────────────────────────────────────────────────

TERMINAL_ALERT_STATUSES: frozenset = frozenset({
    AlertStatus.RESOLVED,
    AlertStatus.EXPIRED,
})

ACTIVE_ALERT_STATUSES: frozenset = frozenset({
    AlertStatus.ACTIVE,
    AlertStatus.ACKNOWLEDGED,
    AlertStatus.ESCALATED,
})
