"""iios/execution/monitoring/alerts/alert_registry.py
==================================================
AlertRegistry — LifecycleAwareMixin store for active Alert objects.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .alert_rule import Alert
from .constants import (
    ACTIVE_ALERT_STATUSES,
    TERMINAL_ALERT_STATUSES,
    DEFAULT_MAX_ALERTS,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AlertType,
    REGISTRY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    AlertEngineNotRunningError,
    AlertNotFoundError,
    AlertRegistryCapacityError,
)

_log = get_logger(__name__)


class AlertRegistry(LifecycleAwareMixin):
    """
    Thread-safe, lifecycle-aware store for Alert domain objects.

    Active alerts (ACTIVE, ACKNOWLEDGED, ESCALATED) live here.
    Terminated alerts (RESOLVED, EXPIRED) should be moved to AlertHistory.
    """

    def __init__(self, max_alerts: int = DEFAULT_MAX_ALERTS) -> None:
        super().__init__()
        self._max_alerts = max(1, max_alerts)
        self._alerts: Dict[str, Alert] = {}
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("AlertRegistry starting.", system_id=REGISTRY_SYSTEM_ID)

    def _on_stop(self) -> None:
        with self._lock:
            active = len(self._alerts)
        _log.info(
            "AlertRegistry stopping.",
            system_id=REGISTRY_SYSTEM_ID,
            active_alerts=active,
        )

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise AlertEngineNotRunningError()

    # ── Writes ────────────────────────────────────────────────────────────────

    def store(self, alert: Alert) -> None:
        """Register a new alert.  Raises if registry is at capacity."""
        self._assert_running()
        with self._lock:
            if len(self._alerts) >= self._max_alerts:
                raise AlertRegistryCapacityError(self._max_alerts)
            self._alerts[alert.alert_id] = alert
        _log.info(
            "Alert stored.",
            alert_id=alert.alert_id,
            alert_type=alert.alert_type.value,
            severity=alert.severity.value,
        )

    def update(self, alert: Alert) -> None:
        """Update an existing alert in place (status change etc.)."""
        self._assert_running()
        with self._lock:
            if alert.alert_id not in self._alerts:
                raise AlertNotFoundError(alert.alert_id)
            self._alerts[alert.alert_id] = alert

    def remove(self, alert_id: str) -> Optional[Alert]:
        """Remove and return an alert.  Returns None if not found."""
        self._assert_running()
        with self._lock:
            return self._alerts.pop(alert_id, None)

    def purge_terminal(self) -> List[Alert]:
        """Remove all alerts in a terminal status.  Returns the removed alerts."""
        self._assert_running()
        with self._lock:
            terminal = [a for a in self._alerts.values() if a.status in TERMINAL_ALERT_STATUSES]
            for a in terminal:
                del self._alerts[a.alert_id]
        return terminal

    # ── Reads ─────────────────────────────────────────────────────────────────

    def get(self, alert_id: str) -> Alert:
        """Return alert by ID.  Raises AlertNotFoundError if missing."""
        self._assert_running()
        with self._lock:
            alert = self._alerts.get(alert_id)
        if alert is None:
            raise AlertNotFoundError(alert_id)
        return alert

    def find(self, alert_id: str) -> Optional[Alert]:
        """Return alert by ID or None."""
        with self._lock:
            return self._alerts.get(alert_id)

    def all_alerts(self) -> List[Alert]:
        with self._lock:
            return list(self._alerts.values())

    def active_alerts(self) -> List[Alert]:
        with self._lock:
            return [a for a in self._alerts.values() if a.status in ACTIVE_ALERT_STATUSES]

    def alerts_for_session(self, session_id: str) -> List[Alert]:
        with self._lock:
            return [a for a in self._alerts.values() if a.session_id == session_id]

    def alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        with self._lock:
            return [a for a in self._alerts.values() if a.alert_type == alert_type]

    def alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        with self._lock:
            return [a for a in self._alerts.values() if a.severity == severity]

    def contains(self, alert_id: str) -> bool:
        with self._lock:
            return alert_id in self._alerts

    def count(self) -> int:
        with self._lock:
            return len(self._alerts)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for a in self._alerts.values() if a.status in ACTIVE_ALERT_STATUSES)

    def clear(self) -> None:
        self._assert_running()
        with self._lock:
            self._alerts.clear()
