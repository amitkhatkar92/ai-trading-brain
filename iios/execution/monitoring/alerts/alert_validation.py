"""iios/execution/monitoring/alerts/alert_validation.py
==================================================
AlertValidator — stateless validation utilities for the alert framework.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .constants import AlertStatus, ThresholdOperator, TERMINAL_ALERT_STATUSES


@dataclass
class AlertValidationResult:
    """Mutable validation result accumulator."""

    is_valid: bool       = True
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class AlertValidator:
    """Stateless validator for alert framework objects."""

    # ── Context ───────────────────────────────────────────────────────────────

    def validate_context(self, context) -> AlertValidationResult:
        result = AlertValidationResult()
        if not getattr(context, "session_id", ""):
            result.add_error("context.session_id must not be empty.")
        if not getattr(context, "portfolio_id", ""):
            result.add_error("context.portfolio_id must not be empty.")
        if getattr(context, "timestamp", 0.0) <= 0.0:
            result.add_error("context.timestamp must be positive.")
        if getattr(context, "metrics", None) is None:
            result.add_error("context.metrics must not be None.")
        return result

    # ── Request ───────────────────────────────────────────────────────────────

    def validate_request(self, request) -> AlertValidationResult:
        result = AlertValidationResult()
        if not getattr(request, "request_id", ""):
            result.add_error("request.request_id must not be empty.")
        if not getattr(request, "session_id", ""):
            result.add_error("request.session_id must not be empty.")
        ctx = getattr(request, "context", None)
        if ctx is None:
            result.add_error("request.context must not be None.")
        else:
            ctx_r = self.validate_context(ctx)
            result.errors.extend(ctx_r.errors)
            result.warnings.extend(ctx_r.warnings)
            if not ctx_r.is_valid:
                result.is_valid = False
        return result

    # ── Threshold ─────────────────────────────────────────────────────────────

    def validate_threshold(self, threshold) -> AlertValidationResult:
        result = AlertValidationResult()
        if not getattr(threshold, "threshold_id", ""):
            result.add_error("threshold.threshold_id must not be empty.")
        if not getattr(threshold, "metric_key", ""):
            result.add_error("threshold.metric_key must not be empty.")
        op = getattr(threshold, "operator", None)
        if op is None:
            result.add_error("threshold.operator must not be None.")
        crit = getattr(threshold, "critical_value", None)
        if crit is None:
            result.add_error("threshold.critical_value must not be None.")
        warn = getattr(threshold, "warning_value", None)
        emrg = getattr(threshold, "emergency_value", None)
        if op in (ThresholdOperator.GT, ThresholdOperator.GTE):
            if warn is not None and crit is not None and warn >= crit:
                result.add_warning(
                    "warning_value should be less than critical_value for GT/GTE thresholds."
                )
            if crit is not None and emrg is not None and crit >= emrg:
                result.add_warning(
                    "critical_value should be less than emergency_value for GT/GTE thresholds."
                )
        return result

    # ── Rule ─────────────────────────────────────────────────────────────────

    def validate_rule(self, rule) -> AlertValidationResult:
        result = AlertValidationResult()
        if not getattr(rule, "rule_id", ""):
            result.add_error("rule.rule_id must not be empty.")
        if not getattr(rule, "rule_name", ""):
            result.add_error("rule.rule_name must not be empty.")
        thresh = getattr(rule, "threshold", None)
        if thresh is None:
            result.add_error("rule.threshold must not be None.")
        else:
            tr = self.validate_threshold(thresh)
            result.errors.extend(tr.errors)
            result.warnings.extend(tr.warnings)
            if not tr.is_valid:
                result.is_valid = False
        return result

    # ── Alert ─────────────────────────────────────────────────────────────────

    def validate_alert(self, alert) -> AlertValidationResult:
        result = AlertValidationResult()
        if not getattr(alert, "alert_id", ""):
            result.add_error("alert.alert_id must not be empty.")
        if not getattr(alert, "session_id", ""):
            result.add_error("alert.session_id must not be empty.")
        if getattr(alert, "severity", None) is None:
            result.add_error("alert.severity must not be None.")
        if getattr(alert, "alert_type", None) is None:
            result.add_error("alert.alert_type must not be None.")
        if not getattr(alert, "title", ""):
            result.add_warning("alert.title is empty.")
        if getattr(alert, "triggered_at", 0.0) <= 0.0:
            result.add_error("alert.triggered_at must be positive.")
        return result

    # ── Transition ────────────────────────────────────────────────────────────

    def validate_transition(
        self,
        alert_id:    str,
        from_status: AlertStatus,
        to_status:   AlertStatus,
    ) -> AlertValidationResult:
        result = AlertValidationResult()
        if from_status in TERMINAL_ALERT_STATUSES:
            result.add_error(
                f"Cannot transition from terminal status '{from_status.value}'."
            )
            return result
        valid_next = _VALID_TRANSITIONS.get(from_status, frozenset())
        if to_status not in valid_next:
            result.add_error(
                f"Invalid transition: '{from_status.value}' → '{to_status.value}'."
            )
        return result


# ── Valid alert status transitions ────────────────────────────────────────────

_VALID_TRANSITIONS: Dict[AlertStatus, frozenset] = {
    AlertStatus.ACTIVE:       frozenset({
        AlertStatus.ACKNOWLEDGED,
        AlertStatus.ESCALATED,
        AlertStatus.RESOLVED,
        AlertStatus.EXPIRED,
        AlertStatus.SUPPRESSED,
    }),
    AlertStatus.ACKNOWLEDGED: frozenset({
        AlertStatus.ESCALATED,
        AlertStatus.RESOLVED,
        AlertStatus.EXPIRED,
    }),
    AlertStatus.ESCALATED:    frozenset({
        AlertStatus.RESOLVED,
        AlertStatus.EXPIRED,
    }),
    AlertStatus.SUPPRESSED:   frozenset({
        AlertStatus.ACTIVE,   # suppression may expire → re-activate
    }),
    AlertStatus.RESOLVED:     frozenset(),
    AlertStatus.EXPIRED:      frozenset(),
}
