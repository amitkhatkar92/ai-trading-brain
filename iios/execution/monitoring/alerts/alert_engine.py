"""iios/execution/monitoring/alerts/alert_engine.py"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.execution.monitoring.monitoring_constants import AlertStatus, DEFAULT_MAX_ALERTS
from iios.execution.monitoring.monitoring_exceptions import AlertStorageOverflowError
from iios.execution.monitoring.alerts.alert_rule import AlertContext, AlertRule
from iios.execution.monitoring.alerts.notification_event import Alert

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Evaluates registered AlertRules against an AlertContext and stores
    triggered Alert objects.

    Thread-safe.
    """

    def __init__(self, max_alerts: int = DEFAULT_MAX_ALERTS) -> None:
        self._rules:     list[AlertRule]      = []
        self._alerts:    list[Alert]          = []
        self._max_alerts = max_alerts
        self._lock       = threading.RLock()

    # ── Rule management ───────────────────────────────────────────────────────

    def register_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self._rules.append(rule)
        logger.debug("AlertEngine: registered rule '%s'", rule.rule_name)

    def unregister_rule(self, rule_name: str) -> None:
        with self._lock:
            self._rules = [r for r in self._rules if r.rule_name != rule_name]

    def rule_names(self) -> list[str]:
        with self._lock:
            return [r.rule_name for r in self._rules]

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, context: AlertContext) -> list[Alert]:
        """Run all enabled rules; store and return any new alerts."""
        with self._lock:
            enabled_rules = [r for r in self._rules if r.enabled]

        new_alerts: list[Alert] = []
        for rule in enabled_rules:
            try:
                triggered = rule.evaluate(context)
                new_alerts.extend(triggered)
            except Exception as exc:
                logger.warning("Alert rule '%s' raised: %s", rule.rule_name, exc)

        if new_alerts:
            with self._lock:
                if len(self._alerts) + len(new_alerts) > self._max_alerts:
                    raise AlertStorageOverflowError(
                        f"Alert store capacity reached ({self._max_alerts})",
                        "EM-042",
                    )
                self._alerts.extend(new_alerts)
            logger.info("AlertEngine: %d new alert(s) triggered", len(new_alerts))
        return new_alerts

    # ── Query ─────────────────────────────────────────────────────────────────

    def active_alerts(self) -> list[Alert]:
        with self._lock:
            return [a for a in self._alerts if a.is_active()]

    def all_alerts(self) -> list[Alert]:
        with self._lock:
            return list(self._alerts)

    def alerts_by_severity(self, severity: Any) -> list[Alert]:
        with self._lock:
            return [a for a in self._alerts if a.severity == severity]

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            active = sum(1 for a in self._alerts if a.is_active())
            return {
                "total_alerts":  len(self._alerts),
                "active_alerts": active,
                "rule_count":    len(self._rules),
            }
