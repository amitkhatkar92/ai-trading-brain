"""iios/execution/monitoring/alerts/alert_manager.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.monitoring.monitoring_constants import AlertSeverity, AlertStatus
from iios.execution.monitoring.monitoring_exceptions import AlertRuleNotFoundError
from iios.execution.monitoring.alerts.alert_engine import AlertEngine
from iios.execution.monitoring.alerts.alert_rule import (
    AlertContext,
    AlertRule,
    HighLatencyRule,
    HighRejectionRateRule,
    MissingFillRule,
    OrderRejectedRule,
    ReconciliationDiscrepancyRule,
)
from iios.execution.monitoring.alerts.notification_event import Alert


def _default_rule_set() -> list[AlertRule]:
    return [
        HighLatencyRule(),
        OrderRejectedRule(),
        HighRejectionRateRule(),
        ReconciliationDiscrepancyRule(),
        MissingFillRule(),
    ]


class AlertManager:
    """
    High-level API over AlertEngine.

    Pre-loads the default rule set and provides convenience methods
    for alert lifecycle management.
    """

    def __init__(
        self,
        engine:    AlertEngine | None = None,
        load_defaults: bool = True,
    ) -> None:
        self._engine = engine or AlertEngine()
        self._lock   = threading.RLock()
        if load_defaults:
            for rule in _default_rule_set():
                self._engine.register_rule(rule)

    # ── Rule management ───────────────────────────────────────────────────────

    def add_rule(self, rule: AlertRule) -> None:
        self._engine.register_rule(rule)

    def remove_rule(self, rule_name: str) -> None:
        self._engine.unregister_rule(rule_name)

    def list_rules(self) -> list[str]:
        return self._engine.rule_names()

    # ── Evaluation ────────────────────────────────────────────────────────────

    def check(self, context: AlertContext) -> list[Alert]:
        return self._engine.evaluate(context)

    # ── Alert lifecycle ───────────────────────────────────────────────────────

    def active_alerts(self) -> list[Alert]:
        return self._engine.active_alerts()

    def all_alerts(self) -> list[Alert]:
        return self._engine.all_alerts()

    def acknowledge(self, alert_id: str, user: str = "system") -> bool:
        for alert in self._engine.all_alerts():
            if alert.alert_id == alert_id:
                alert.acknowledge(user)
                return True
        return False

    def resolve(self, alert_id: str, reason: str = "") -> bool:
        for alert in self._engine.all_alerts():
            if alert.alert_id == alert_id:
                alert.resolve(reason)
                return True
        return False

    def critical_alerts(self) -> list[Alert]:
        return self._engine.alerts_by_severity(AlertSeverity.CRITICAL)

    def statistics(self) -> dict[str, Any]:
        return self._engine.statistics()
