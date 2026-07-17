"""iios/execution/monitoring/alerts/__init__.py
==================================================
Public surface of the Execution Alert Framework (C6 Phase 6, Module 4).

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

# ── Constants & enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTIVE_ALERT_STATUSES,
    ALERT_TYPE_CATEGORY,
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_EXPIRY_SECONDS,
    DEFAULT_MAX_ALERTS,
    DEFAULT_MAX_ESCALATIONS,
    DEFAULT_MAX_HISTORY,
    ENGINE_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    SEVERITY_WEIGHT,
    TERMINAL_ALERT_STATUSES,
    VERSION,
    AlertCategory,
    AlertEventType,
    AlertPolicyType,
    AlertSeverity,
    AlertStatus,
    AlertType,
    ThresholdOperator,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    AlertEngineNotRunningError,
    AlertFrameworkError,
    AlertNotFoundError,
    AlertRegistryCapacityError,
    AlertRuleEvaluationError,
    AlertRuleNotFoundError,
    AlertSnapshotError,
    AlertTransitionError,
    AlertValidationError,
    DuplicateAlertRuleError,
)

# ── Threshold ─────────────────────────────────────────────────────────────────
from .alert_threshold import AlertThreshold, make_alert_threshold

# ── Context / DTOs ────────────────────────────────────────────────────────────
from .alert_context import AlertContext, make_alert_context
from .alert_request import AlertRequest, make_alert_request
from .alert_response import AlertResponse, make_alert_response
from .alert_snapshot import AlertSnapshot, make_alert_snapshot

# ── Domain events ─────────────────────────────────────────────────────────────
from .alert_events import (
    AlertEvent,
    make_alert_acknowledged,
    make_alert_escalated,
    make_alert_expired,
    make_alert_generated,
    make_alert_resolved,
    make_alert_suppressed,
)

# ── Policy ────────────────────────────────────────────────────────────────────
from .alert_policy import (
    AlertPolicy,
    PolicyEvaluator,
    make_alert_policy,
    make_consecutive_policy,
    make_immediate_policy,
    make_rolling_window_policy,
)

# ── Rule (Alert domain object + abstract base + built-in rules) ───────────────
from .alert_rule import (
    Alert,
    AlertRule,
    BrokerUnavailableRule,
    ExecutionFailureRateRule,
    GatewayDegradedRule,
    HighLatencyRule,
    MonitoringFailureRule,
    QueueCongestionRule,
    ResourceExhaustionRule,
    RetryThresholdExceededRule,
    SubsystemUnhealthyRule,
    TimeoutThresholdExceededRule,
)

# ── Supporting components ─────────────────────────────────────────────────────
from .alert_history import AlertHistory
from .alert_statistics import AlertStatistics
from .alert_validation import AlertValidationResult, AlertValidator

# ── Infrastructure ────────────────────────────────────────────────────────────
from .alert_registry import AlertRegistry
from .alert_factory import AlertFactory

# ── Primary API ───────────────────────────────────────────────────────────────
from .alert_engine import AlertEngine
from .alert_manager import AlertManager

__all__ = [
    # constants
    "ACTIVE_ALERT_STATUSES",
    "ALERT_TYPE_CATEGORY",
    "DEFAULT_COOLDOWN_SECONDS",
    "DEFAULT_EXPIRY_SECONDS",
    "DEFAULT_MAX_ALERTS",
    "DEFAULT_MAX_ESCALATIONS",
    "DEFAULT_MAX_HISTORY",
    "ENGINE_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "SEVERITY_WEIGHT",
    "TERMINAL_ALERT_STATUSES",
    "VERSION",
    "AlertCategory",
    "AlertEventType",
    "AlertPolicyType",
    "AlertSeverity",
    "AlertStatus",
    "AlertType",
    "ThresholdOperator",
    # exceptions
    "AlertEngineNotRunningError",
    "AlertFrameworkError",
    "AlertNotFoundError",
    "AlertRegistryCapacityError",
    "AlertRuleEvaluationError",
    "AlertRuleNotFoundError",
    "AlertSnapshotError",
    "AlertTransitionError",
    "AlertValidationError",
    "DuplicateAlertRuleError",
    # threshold
    "AlertThreshold",
    "make_alert_threshold",
    # context / DTOs
    "AlertContext",
    "make_alert_context",
    "AlertRequest",
    "make_alert_request",
    "AlertResponse",
    "make_alert_response",
    "AlertSnapshot",
    "make_alert_snapshot",
    # events
    "AlertEvent",
    "make_alert_acknowledged",
    "make_alert_escalated",
    "make_alert_expired",
    "make_alert_generated",
    "make_alert_resolved",
    "make_alert_suppressed",
    # policy
    "AlertPolicy",
    "PolicyEvaluator",
    "make_alert_policy",
    "make_consecutive_policy",
    "make_immediate_policy",
    "make_rolling_window_policy",
    # rules
    "Alert",
    "AlertRule",
    "BrokerUnavailableRule",
    "ExecutionFailureRateRule",
    "GatewayDegradedRule",
    "HighLatencyRule",
    "MonitoringFailureRule",
    "QueueCongestionRule",
    "ResourceExhaustionRule",
    "RetryThresholdExceededRule",
    "SubsystemUnhealthyRule",
    "TimeoutThresholdExceededRule",
    # supporting components
    "AlertHistory",
    "AlertStatistics",
    "AlertValidationResult",
    "AlertValidator",
    # infrastructure
    "AlertRegistry",
    "AlertFactory",
    # primary API
    "AlertEngine",
    "AlertManager",
]
