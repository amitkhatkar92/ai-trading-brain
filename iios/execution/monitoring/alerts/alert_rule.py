"""iios/execution/monitoring/alerts/alert_rule.py
==================================================
Alert — mutable core alert domain object.
AlertRule — abstract base class for all evaluation rules.
Built-in rules for all 10 supported alert types.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .alert_context import AlertContext
from .alert_policy import AlertPolicy, make_immediate_policy
from .alert_threshold import AlertThreshold, make_alert_threshold
from .constants import (
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AlertType,
    DEFAULT_BROKER_UTIL_CRITICAL,
    DEFAULT_EXPIRY_SECONDS,
    DEFAULT_FAILURE_RATE_CRITICAL,
    DEFAULT_FAILURE_RATE_WARNING,
    DEFAULT_GATEWAY_THROUGHPUT_MIN,
    DEFAULT_LATENCY_CRITICAL_MS,
    DEFAULT_LATENCY_EMERGENCY_MS,
    DEFAULT_LATENCY_WARNING_MS,
    DEFAULT_QUEUE_WAIT_CRITICAL_MS,
    DEFAULT_QUEUE_WAIT_WARNING_MS,
    DEFAULT_RETRY_RATE_CRITICAL,
    DEFAULT_RETRY_RATE_WARNING,
    DEFAULT_TIMEOUT_RATE_CRITICAL,
    DEFAULT_TIMEOUT_RATE_WARNING,
    TERMINAL_ALERT_STATUSES,
    VERSION,
    ThresholdOperator,
)


# ── Alert domain object ───────────────────────────────────────────────────────

@dataclass
class Alert:
    """
    Mutable core alert domain object.

    Represents a single condition breach detected by an AlertRule.
    Supports lifecycle transitions:
      ACTIVE → ACKNOWLEDGED → ESCALATED → RESOLVED / EXPIRED
      ACTIVE → SUPPRESSED → ACTIVE (if suppression expires)
    """

    alert_id:          str
    alert_type:        AlertType
    severity:          AlertSeverity
    category:          AlertCategory
    status:            AlertStatus
    rule_id:           str
    rule_name:         str
    title:             str
    message:           str
    session_id:        str
    portfolio_id:      str
    triggered_at:      float
    detected_at:       float
    framework_version: str

    gateway_id:         Optional[str]   = None
    strategy_id:        Optional[str]   = None
    metric_key:         Optional[str]   = None
    threshold_value:    Optional[float] = None
    actual_value:       Optional[float] = None
    acknowledged_at:    Optional[float] = None
    acknowledged_by:    Optional[str]   = None
    resolved_at:        Optional[float] = None
    resolved_by:        Optional[str]   = None
    resolution_notes:   Optional[str]   = None
    expires_at:         Optional[float] = None
    escalated_at:       Optional[float] = None
    escalation_count:   int             = 0
    suppressed:         bool            = False
    suppression_reason: Optional[str]   = None
    correlation_id:     Optional[str]   = None
    metadata:           Dict[str, Any]  = field(default_factory=dict)

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def acknowledge(self, actor: str, notes: str = "") -> None:
        """Transition ACTIVE → ACKNOWLEDGED."""
        if self.status != AlertStatus.ACTIVE:
            return
        self.status          = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = time.time()
        self.acknowledged_by = actor
        if notes:
            self.metadata["acknowledgement_notes"] = notes

    def escalate(self, actor: str = "engine") -> None:
        """Transition ACTIVE/ACKNOWLEDGED → ESCALATED."""
        if self.status not in (AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED):
            return
        self.status           = AlertStatus.ESCALATED
        self.escalated_at     = time.time()
        self.escalation_count += 1
        self.metadata["escalated_by"] = actor

    def resolve(self, actor: str, notes: str = "") -> None:
        """Transition any non-terminal status → RESOLVED."""
        if self.status in TERMINAL_ALERT_STATUSES:
            return
        self.status           = AlertStatus.RESOLVED
        self.resolved_at      = time.time()
        self.resolved_by      = actor
        self.resolution_notes = notes

    def expire(self) -> None:
        """Transition any non-terminal status → EXPIRED."""
        if self.status in TERMINAL_ALERT_STATUSES:
            return
        self.status = AlertStatus.EXPIRED

    def suppress(self, reason: str = "") -> None:
        """Transition ACTIVE → SUPPRESSED."""
        if self.status != AlertStatus.ACTIVE:
            return
        self.status             = AlertStatus.SUPPRESSED
        self.suppressed         = True
        self.suppression_reason = reason

    def reactivate(self) -> None:
        """Transition SUPPRESSED → ACTIVE (suppression expiry)."""
        if self.status != AlertStatus.SUPPRESSED:
            return
        self.status = AlertStatus.ACTIVE

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_active(self) -> bool:
        return self.status == AlertStatus.ACTIVE

    def is_terminal(self) -> bool:
        return self.status in TERMINAL_ALERT_STATUSES

    def is_stale(self, now: Optional[float] = None) -> bool:
        """Return True if expires_at has passed."""
        if self.expires_at is None:
            return False
        return (now or time.time()) >= self.expires_at

    def duration_seconds(self, now: Optional[float] = None) -> float:
        end = self.resolved_at or self.expires_at or (now or time.time())
        return max(0.0, end - self.detected_at)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id":          self.alert_id,
            "alert_type":        self.alert_type.value,
            "severity":          self.severity.value,
            "category":          self.category.value,
            "status":            self.status.value,
            "rule_id":           self.rule_id,
            "rule_name":         self.rule_name,
            "title":             self.title,
            "message":           self.message,
            "session_id":        self.session_id,
            "portfolio_id":      self.portfolio_id,
            "gateway_id":        self.gateway_id,
            "metric_key":        self.metric_key,
            "threshold_value":   self.threshold_value,
            "actual_value":      self.actual_value,
            "triggered_at":      self.triggered_at,
            "detected_at":       self.detected_at,
            "acknowledged_at":   self.acknowledged_at,
            "resolved_at":       self.resolved_at,
            "escalated_at":      self.escalated_at,
            "escalation_count":  self.escalation_count,
            "suppressed":        self.suppressed,
            "expires_at":        self.expires_at,
            "framework_version": self.framework_version,
        }


# ── Abstract base rule ────────────────────────────────────────────────────────

class AlertRule(abc.ABC):
    """
    Abstract base for all alert evaluation rules.

    Subclasses define ``rule_name``, ``alert_type``, ``category``,
    ``threshold``, and ``policy`` as class attributes, then implement
    ``evaluate()``.

    The rule NEVER computes metrics — it only reads from AlertContext.
    """

    rule_id:    str        = ""
    rule_name:  str        = ""
    alert_type: AlertType  = AlertType.MONITORING_FAILURE
    category:   AlertCategory = AlertCategory.OPERATIONAL
    threshold:  AlertThreshold = None   # type: ignore[assignment]
    policy:     AlertPolicy    = None   # type: ignore[assignment]
    enabled:    bool       = True

    def __init__(
        self,
        rule_id:    Optional[str] = None,
        *,
        enabled:   bool                     = True,
        threshold: Optional[AlertThreshold] = None,
        policy:    Optional[AlertPolicy]    = None,
    ) -> None:
        # Assign rule_id: passed > class attribute > generated
        if rule_id is not None:
            self.rule_id = rule_id
        elif not self.rule_id:
            self.rule_id = str(uuid.uuid4())
        if threshold is not None:
            self.threshold = threshold
        if policy is not None:
            self.policy = policy
        self.enabled = enabled

    @abc.abstractmethod
    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        """
        Evaluate the rule against ``context``.

        Returns an Alert if a condition is breached, ``None`` otherwise.
        MUST NOT modify context or compute metrics.
        """

    def is_enabled(self) -> bool:
        return self.enabled

    # ── Protected helpers ─────────────────────────────────────────────────────

    def _make_alert(
        self,
        context:         AlertContext,
        severity:        AlertSeverity,
        title:           str,
        message:         str,
        *,
        metric_key:      Optional[str]   = None,
        threshold_value: Optional[float] = None,
        actual_value:    Optional[float] = None,
        correlation_id:  Optional[str]   = None,
        expiry_seconds:  float           = DEFAULT_EXPIRY_SECONDS,
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> Alert:
        now = time.time()
        return Alert(
            alert_id          = str(uuid.uuid4()),
            alert_type        = self.alert_type,
            severity          = severity,
            category          = self.category,
            status            = AlertStatus.ACTIVE,
            rule_id           = self.rule_id,
            rule_name         = self.rule_name,
            title             = title,
            message           = message,
            session_id        = context.session_id,
            portfolio_id      = context.portfolio_id,
            triggered_at      = context.timestamp,
            detected_at       = now,
            framework_version = VERSION,
            gateway_id        = context.gateway_id,
            strategy_id       = context.strategy_id,
            metric_key        = metric_key,
            threshold_value   = threshold_value,
            actual_value      = actual_value,
            expires_at        = now + expiry_seconds if expiry_seconds > 0 else None,
            correlation_id    = correlation_id,
            metadata          = dict(metadata) if metadata else {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":    self.rule_id,
            "rule_name":  self.rule_name,
            "alert_type": self.alert_type.value,
            "category":   self.category.value,
            "enabled":    self.enabled,
            "threshold":  self.threshold.to_dict() if self.threshold else None,
            "policy":     self.policy.to_dict() if self.policy else None,
        }


# ── Built-in rules ────────────────────────────────────────────────────────────

class HighLatencyRule(AlertRule):
    """Fires when P99 execution latency exceeds threshold."""

    rule_name  = "high_latency"
    alert_type = AlertType.HIGH_LATENCY
    category   = AlertCategory.LATENCY
    threshold  = make_alert_threshold(
        "p99_latency", ThresholdOperator.GT, DEFAULT_LATENCY_CRITICAL_MS,
        warning_value=DEFAULT_LATENCY_WARNING_MS, emergency_value=DEFAULT_LATENCY_EMERGENCY_MS,
        unit="ms", description="P99 execution latency threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        actual = context.get_metric("p99_latency") or context.get_metric("max_latency")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, sv,
            title=f"High Execution Latency [{sv.value.upper()}]",
            message=f"P99 latency {actual:.1f}ms exceeds {self.threshold.critical_value:.0f}ms threshold.",
            metric_key="p99_latency", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class QueueCongestionRule(AlertRule):
    """Fires when queue wait time exceeds threshold."""

    rule_name  = "queue_congestion"
    alert_type = AlertType.QUEUE_CONGESTION
    category   = AlertCategory.QUEUE
    threshold  = make_alert_threshold(
        "queue_wait_time", ThresholdOperator.GT, DEFAULT_QUEUE_WAIT_CRITICAL_MS,
        warning_value=DEFAULT_QUEUE_WAIT_WARNING_MS, unit="ms",
        description="Queue wait time threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        actual = context.get_metric("queue_wait_time")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, sv,
            title=f"Queue Congestion [{sv.value.upper()}]",
            message=f"Queue wait time {actual:.1f}ms exceeds {self.threshold.critical_value:.0f}ms threshold.",
            metric_key="queue_wait_time", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class ExecutionFailureRateRule(AlertRule):
    """Fires when execution failure rate exceeds threshold."""

    rule_name  = "execution_failure_rate"
    alert_type = AlertType.EXECUTION_FAILURE_RATE
    category   = AlertCategory.EXECUTION_PERFORMANCE
    threshold  = make_alert_threshold(
        "failure_rate", ThresholdOperator.GT, DEFAULT_FAILURE_RATE_CRITICAL,
        warning_value=DEFAULT_FAILURE_RATE_WARNING, emergency_value=DEFAULT_FAILURE_RATE_CRITICAL * 2,
        description="Execution failure rate threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        actual = context.get_metric("failure_rate")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, sv,
            title=f"High Execution Failure Rate [{sv.value.upper()}]",
            message=f"Failure rate {actual:.1%} exceeds {self.threshold.critical_value:.1%} threshold.",
            metric_key="failure_rate", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class BrokerUnavailableRule(AlertRule):
    """Fires when broker utilisation is critically high."""

    rule_name  = "broker_unavailable"
    alert_type = AlertType.BROKER_UNAVAILABLE
    category   = AlertCategory.BROKER
    threshold  = make_alert_threshold(
        "broker_utilization", ThresholdOperator.GTE, DEFAULT_BROKER_UTIL_CRITICAL,
        description="Broker utilization threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        actual = context.get_metric("broker_utilization")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, sv,
            title=f"Broker Unavailable / Saturated [{sv.value.upper()}]",
            message=f"Broker utilisation {actual:.1%} at or above {self.threshold.critical_value:.0%} threshold.",
            metric_key="broker_utilization", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class GatewayDegradedRule(AlertRule):
    """Fires when gateway throughput falls below minimum threshold."""

    rule_name  = "gateway_degraded"
    alert_type = AlertType.GATEWAY_DEGRADED
    category   = AlertCategory.GATEWAY
    threshold  = make_alert_threshold(
        "gateway_throughput", ThresholdOperator.LTE, DEFAULT_GATEWAY_THROUGHPUT_MIN,
        description="Gateway throughput minimum threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        if not context.has_metric("gateway_throughput"):
            return None
        actual = context.get_metric("gateway_throughput")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, AlertSeverity.HIGH,
            title="Gateway Degraded",
            message=f"Gateway throughput {actual:.2f} at or below {self.threshold.critical_value:.2f} minimum.",
            metric_key="gateway_throughput", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class RetryThresholdExceededRule(AlertRule):
    """Fires when order retry rate exceeds threshold."""

    rule_name  = "retry_threshold_exceeded"
    alert_type = AlertType.RETRY_THRESHOLD_EXCEEDED
    category   = AlertCategory.RELIABILITY
    threshold  = make_alert_threshold(
        "retry_rate", ThresholdOperator.GT, DEFAULT_RETRY_RATE_CRITICAL,
        warning_value=DEFAULT_RETRY_RATE_WARNING, description="Order retry rate threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        actual = context.get_metric("retry_rate")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, sv,
            title=f"Retry Threshold Exceeded [{sv.value.upper()}]",
            message=f"Order retry rate {actual:.1%} exceeds {self.threshold.critical_value:.1%} threshold.",
            metric_key="retry_rate", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class TimeoutThresholdExceededRule(AlertRule):
    """Fires when order timeout rate exceeds threshold."""

    rule_name  = "timeout_threshold_exceeded"
    alert_type = AlertType.TIMEOUT_THRESHOLD_EXCEEDED
    category   = AlertCategory.RELIABILITY
    threshold  = make_alert_threshold(
        "timeout_rate", ThresholdOperator.GT, DEFAULT_TIMEOUT_RATE_CRITICAL,
        warning_value=DEFAULT_TIMEOUT_RATE_WARNING, description="Order timeout rate threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        actual = context.get_metric("timeout_rate")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, sv,
            title=f"Timeout Threshold Exceeded [{sv.value.upper()}]",
            message=f"Timeout rate {actual:.1%} exceeds {self.threshold.critical_value:.1%} threshold.",
            metric_key="timeout_rate", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class MonitoringFailureRule(AlertRule):
    """Fires when the monitoring cycle itself is unhealthy (high cycle time)."""

    rule_name  = "monitoring_failure"
    alert_type = AlertType.MONITORING_FAILURE
    category   = AlertCategory.OPERATIONAL
    threshold  = make_alert_threshold(
        "monitoring_cycle_time", ThresholdOperator.GT, 5_000.0,
        warning_value=2_000.0, unit="ms", description="Monitoring cycle time threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        actual = context.get_metric("monitoring_cycle_time")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, sv,
            title=f"Monitoring Failure [{sv.value.upper()}]",
            message=f"Monitoring cycle time {actual:.0f}ms exceeds {self.threshold.critical_value:.0f}ms threshold.",
            metric_key="monitoring_cycle_time", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class ResourceExhaustionRule(AlertRule):
    """Fires when execution count is unusually high (resource exhaustion proxy)."""

    rule_name  = "resource_exhaustion"
    alert_type = AlertType.RESOURCE_EXHAUSTION
    category   = AlertCategory.INFRASTRUCTURE
    threshold  = make_alert_threshold(
        "execution_count", ThresholdOperator.GT, 10_000.0,
        warning_value=5_000.0, description="Execution count upper bound (resource exhaustion proxy)",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        actual = context.get_metric("execution_count")
        sv = self.threshold.evaluate(actual)
        if sv is None:
            return None
        return self._make_alert(
            context, sv,
            title=f"Resource Exhaustion [{sv.value.upper()}]",
            message=(
                f"Execution count {actual:.0f} exceeds "
                f"{self.threshold.critical_value:.0f} threshold, "
                "indicating possible resource exhaustion."
            ),
            metric_key="execution_count", threshold_value=self.threshold.critical_value, actual_value=actual,
        )


class SubsystemUnhealthyRule(AlertRule):
    """
    Composite rule: fires when multiple conditions are simultaneously breached,
    indicating a broader subsystem outage.
    """

    rule_name  = "subsystem_unhealthy"
    alert_type = AlertType.SUBSYSTEM_UNHEALTHY
    category   = AlertCategory.AVAILABILITY
    threshold  = make_alert_threshold(
        "failure_rate", ThresholdOperator.GT, 0.15,
        warning_value=0.08, emergency_value=0.30,
        description="Composite subsystem health threshold",
    )
    policy = make_immediate_policy()

    def evaluate(self, context: AlertContext) -> Optional[Alert]:
        failure_rate = context.get_metric("failure_rate")
        p99_latency  = context.get_metric("p99_latency")
        timeout_rate = context.get_metric("timeout_rate")

        conditions_breached = sum([
            failure_rate > 0.08,
            p99_latency  > DEFAULT_LATENCY_WARNING_MS,
            timeout_rate > DEFAULT_TIMEOUT_RATE_WARNING,
        ])
        if conditions_breached < 2:
            return None

        sv = self.threshold.evaluate(failure_rate) or AlertSeverity.HIGH
        return self._make_alert(
            context, sv,
            title=f"Subsystem Unhealthy [{sv.value.upper()}]",
            message=(
                f"Multiple conditions breached: "
                f"failure_rate={failure_rate:.1%}, "
                f"p99_latency={p99_latency:.1f}ms, "
                f"timeout_rate={timeout_rate:.1%}."
            ),
            metadata={
                "conditions_breached": conditions_breached,
                "failure_rate":        failure_rate,
                "p99_latency":         p99_latency,
                "timeout_rate":        timeout_rate,
            },
        )
