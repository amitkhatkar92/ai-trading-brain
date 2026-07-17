"""iios/execution/monitoring/alerts/alert_threshold.py
==================================================
AlertThreshold — immutable threshold configuration for alert rules.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import AlertSeverity, ThresholdOperator


@dataclass(frozen=True)
class AlertThreshold:
    """
    Immutable threshold configuration for a single metric condition.

    Supports three severity tiers: warning (optional), critical (required),
    and emergency (optional).

    Fields
    ------
    threshold_id    : unique ID for this threshold config
    metric_key      : dot-key of the metric to evaluate (e.g. ``p99_latency``)
    operator        : comparison operator applied to the actual value
    critical_value  : value that triggers a CRITICAL alert
    warning_value   : optional value that triggers a WARNING pre-alert
    emergency_value : optional value that triggers an EMERGENCY alert
    description     : human-readable description
    unit            : optional unit label (ms, %, count …)
    metadata        : arbitrary annotations
    """

    threshold_id:    str
    metric_key:      str
    operator:        ThresholdOperator
    critical_value:  float

    warning_value:   Optional[float] = None
    emergency_value: Optional[float] = None
    description:     str             = ""
    unit:            str             = ""
    metadata:        Dict[str, Any]  = field(default_factory=dict)

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, actual: float) -> Optional[AlertSeverity]:
        """
        Return the highest triggered severity, or ``None`` if no threshold
        is breached.  Emergency > Critical > Warning.
        """
        if self.emergency_value is not None and self._compare(actual, self.emergency_value):
            return AlertSeverity.EMERGENCY
        if self._compare(actual, self.critical_value):
            return AlertSeverity.CRITICAL
        if self.warning_value is not None and self._compare(actual, self.warning_value):
            return AlertSeverity.WARNING
        return None

    def is_breached(self, actual: float) -> bool:
        """Return ``True`` if any tier is breached."""
        return self.evaluate(actual) is not None

    def _compare(self, actual: float, threshold: float) -> bool:
        op = self.operator
        if op == ThresholdOperator.GT:
            return actual > threshold
        if op == ThresholdOperator.GTE:
            return actual >= threshold
        if op == ThresholdOperator.LT:
            return actual < threshold
        if op == ThresholdOperator.LTE:
            return actual <= threshold
        if op == ThresholdOperator.EQ:
            return actual == threshold
        if op == ThresholdOperator.NEQ:
            return actual != threshold
        return False  # pragma: no cover

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold_id":    self.threshold_id,
            "metric_key":      self.metric_key,
            "operator":        self.operator.value,
            "critical_value":  self.critical_value,
            "warning_value":   self.warning_value,
            "emergency_value": self.emergency_value,
            "description":     self.description,
            "unit":            self.unit,
        }


def make_alert_threshold(
    metric_key:     str,
    operator:       ThresholdOperator,
    critical_value: float,
    *,
    warning_value:   Optional[float] = None,
    emergency_value: Optional[float] = None,
    description:     str             = "",
    unit:            str             = "",
    threshold_id:    Optional[str]   = None,
) -> AlertThreshold:
    """Factory for AlertThreshold."""
    return AlertThreshold(
        threshold_id    = threshold_id or str(uuid.uuid4()),
        metric_key      = metric_key,
        operator        = operator,
        critical_value  = critical_value,
        warning_value   = warning_value,
        emergency_value = emergency_value,
        description     = description,
        unit            = unit,
    )
