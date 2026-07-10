"""iios/execution/monitoring/alerts/alert_rule.py"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    AlertSeverity,
    DEFAULT_HIGH_LATENCY_THRESHOLD_MS,
    DEFAULT_REJECTION_RATE_THRESHOLD,
    ExecutionRecordStatus,
)
from iios.execution.monitoring.alerts.notification_event import Alert


@dataclass
class AlertContext:
    """Data snapshot passed to each AlertRule for evaluation."""

    execution_records:      list[Any] = field(default_factory=list)   # list[ExecutionRecord]
    fill_records:           list[Any] = field(default_factory=list)   # list[FillRecord]
    latency_values_ms:      list[float] = field(default_factory=list)
    reconciliation_reports: list[Any] = field(default_factory=list)
    timestamp:              float = field(default_factory=time.time)


class AlertRule(abc.ABC):
    """Abstract base for all alert evaluation rules."""

    rule_name: str = "base_rule"
    severity:  AlertSeverity = AlertSeverity.MEDIUM
    enabled:   bool = True

    @abc.abstractmethod
    def evaluate(self, context: AlertContext) -> list[Alert]:
        """Evaluate the rule against *context*; return list of triggered alerts."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "severity":  self.severity.value,
            "enabled":   self.enabled,
        }


# ── Concrete rules ────────────────────────────────────────────────────────────

class HighLatencyRule(AlertRule):
    """Triggers when average execution latency exceeds *threshold_ms*."""

    rule_name = "high_latency"
    severity  = AlertSeverity.HIGH

    def __init__(self, threshold_ms: float = DEFAULT_HIGH_LATENCY_THRESHOLD_MS) -> None:
        self.threshold_ms = threshold_ms

    def evaluate(self, context: AlertContext) -> list[Alert]:
        values = context.latency_values_ms
        if not values:
            return []
        avg = sum(values) / len(values)
        if avg <= self.threshold_ms:
            return []
        return [Alert(
            rule_name=self.rule_name,
            severity=self.severity,
            title="High Execution Latency",
            message=f"Average latency {avg:.1f}ms exceeds threshold {self.threshold_ms:.1f}ms",
            entity_type="system",
            metadata={"avg_latency_ms": avg, "threshold_ms": self.threshold_ms},
        )]


class OrderRejectedRule(AlertRule):
    """Triggers for every rejected execution."""

    rule_name = "order_rejected"
    severity  = AlertSeverity.HIGH

    def evaluate(self, context: AlertContext) -> list[Alert]:
        alerts = []
        for rec in context.execution_records:
            if rec.status == ExecutionRecordStatus.REJECTED:
                alerts.append(Alert(
                    rule_name=self.rule_name,
                    severity=self.severity,
                    title="Order Rejected",
                    message=f"Order {rec.order_id} rejected: {rec.rejection_reason}",
                    entity_id=rec.order_id,
                    entity_type="order",
                    broker_id=rec.broker_id,
                    metadata={"execution_id": rec.execution_id},
                ))
        return alerts


class HighRejectionRateRule(AlertRule):
    """Triggers when the rejection rate exceeds *threshold*."""

    rule_name = "high_rejection_rate"
    severity  = AlertSeverity.CRITICAL

    def __init__(self, threshold: float = DEFAULT_REJECTION_RATE_THRESHOLD) -> None:
        self.threshold = threshold

    def evaluate(self, context: AlertContext) -> list[Alert]:
        records = context.execution_records
        if not records:
            return []
        rejected = sum(1 for r in records if r.status == ExecutionRecordStatus.REJECTED)
        rate = rejected / len(records)
        if rate <= self.threshold:
            return []
        return [Alert(
            rule_name=self.rule_name,
            severity=self.severity,
            title="High Rejection Rate",
            message=f"Rejection rate {rate:.1%} exceeds threshold {self.threshold:.1%}",
            entity_type="system",
            metadata={"rejection_rate": rate, "threshold": self.threshold},
        )]


class ReconciliationDiscrepancyRule(AlertRule):
    """Triggers when a reconciliation report is not clean."""

    rule_name = "reconciliation_discrepancy"
    severity  = AlertSeverity.HIGH

    def evaluate(self, context: AlertContext) -> list[Alert]:
        alerts = []
        for report in context.reconciliation_reports:
            if not report.is_clean():
                alerts.append(Alert(
                    rule_name=self.rule_name,
                    severity=self.severity,
                    title="Reconciliation Discrepancy",
                    message=(
                        f"Reconciliation {report.reconciliation_id[:8]}: "
                        f"{report.discrepant} discrepant, "
                        f"{report.missing_internal} missing internally, "
                        f"{report.missing_external} missing externally"
                    ),
                    entity_type="reconciliation",
                    entity_id=report.reconciliation_id,
                    metadata=report.to_dict(),
                ))
        return alerts


class MissingFillRule(AlertRule):
    """Triggers when an accepted order has no fill within *timeout_sec*."""

    rule_name = "missing_fill"
    severity  = AlertSeverity.HIGH

    def __init__(self, timeout_sec: float = 60.0) -> None:
        self.timeout_sec = timeout_sec

    def evaluate(self, context: AlertContext) -> list[Alert]:
        now    = context.timestamp
        alerts = []
        for rec in context.execution_records:
            if rec.status == ExecutionRecordStatus.ACCEPTED and rec.accepted_at is not None:
                age = now - rec.accepted_at
                if age >= self.timeout_sec and rec.fill_count == 0:
                    alerts.append(Alert(
                        rule_name=self.rule_name,
                        severity=self.severity,
                        title="Missing Fill",
                        message=(
                            f"Order {rec.order_id} accepted {age:.0f}s ago "
                            f"with no fill (timeout={self.timeout_sec:.0f}s)"
                        ),
                        entity_id=rec.order_id,
                        entity_type="order",
                        broker_id=rec.broker_id,
                        metadata={"age_sec": age, "timeout_sec": self.timeout_sec},
                    ))
        return alerts
