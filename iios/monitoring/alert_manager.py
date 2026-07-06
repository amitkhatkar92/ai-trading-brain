"""
iios/monitoring/alert_manager.py
==================================
Alert generation, deduplication, suppression, and routing.

``AlertManager`` receives conditions from any IIOS subsystem, deduplicates
them by fingerprint, suppresses repeated alerts during a cooldown window,
and routes them to registered handlers.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Optional

from .monitoring_constants import AlertLevel, AlertStatus, ALERT_COOLDOWN_SECONDS, MAX_RECENT_ALERTS
from .monitoring_models import AlertEvent

__all__ = [
    "AlertManager",
    "AlertHandler",
    "get_alert_manager",
]

_LOG = logging.getLogger("iios.monitoring.alerts")
_instance_lock = threading.Lock()
_instance: Optional["AlertManager"] = None

AlertHandler = Callable[[AlertEvent], None]


class AlertManager:
    """Generates, deduplicates, and routes alerts.

    Args:
        cooldown_seconds: Minimum time (s) between repeated alerts for the same
                          fingerprint.
        max_history:      Maximum alerts to retain in memory.
    """

    def __init__(
        self,
        cooldown_seconds: int = ALERT_COOLDOWN_SECONDS,
        max_history: int = MAX_RECENT_ALERTS,
    ) -> None:
        self._lock = threading.Lock()
        self._cooldown = cooldown_seconds
        # fingerprint → last fire time (monotonic)
        self._last_fired: dict[str, float] = {}
        # All open alerts: fingerprint → AlertEvent
        self._open: dict[str, AlertEvent] = {}
        # History deque
        self._history: deque[AlertEvent] = deque(maxlen=max_history)
        # Handlers per level
        self._handlers: dict[str, list[AlertHandler]] = {
            AlertLevel.INFO.value:     [],
            AlertLevel.WARNING.value:  [],
            AlertLevel.ERROR.value:    [],
            AlertLevel.CRITICAL.value: [],
            "*": [],
        }
        self._alert_count = 0

    # ------------------------------------------------------------------
    # Alert generation
    # ------------------------------------------------------------------

    def fire(
        self,
        level: str,
        title: str,
        message: str,
        component: str = "",
        layer: str = "",
        metric_name: str = "",
        metric_value: Optional[float] = None,
        threshold: Optional[float] = None,
        correlation_id: str = "",
        **tags: str,
    ) -> Optional[AlertEvent]:
        """Generate an alert, applying deduplication and cooldown.

        Returns the ``AlertEvent`` if it was fired, or ``None`` if suppressed.
        """
        alert = AlertEvent(
            level=level,
            title=title,
            message=message,
            component=component,
            layer=layer,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
            correlation_id=correlation_id,
            tags=dict(tags),
        )

        fingerprint = alert.fingerprint
        now = time.monotonic()

        with self._lock:
            last = self._last_fired.get(fingerprint, 0.0)
            if (now - last) < self._cooldown:
                # Suppress — still within cooldown window
                alert.status = AlertStatus.SUPPRESSED.value
                return None

            self._last_fired[fingerprint] = now
            self._open[fingerprint] = alert
            self._history.append(alert)
            self._alert_count += 1
            handlers = self._collect_handlers(level)

        # Route to handlers outside the lock
        self._route(alert, handlers)
        return alert

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def info(self, title: str, message: str, **kwargs: Any) -> Optional[AlertEvent]:
        return self.fire(AlertLevel.INFO.value, title, message, **kwargs)

    def warning(self, title: str, message: str, **kwargs: Any) -> Optional[AlertEvent]:
        return self.fire(AlertLevel.WARNING.value, title, message, **kwargs)

    def error(self, title: str, message: str, **kwargs: Any) -> Optional[AlertEvent]:
        return self.fire(AlertLevel.ERROR.value, title, message, **kwargs)

    def critical(self, title: str, message: str, **kwargs: Any) -> Optional[AlertEvent]:
        return self.fire(AlertLevel.CRITICAL.value, title, message, **kwargs)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self, fingerprint: str, reason: str = "") -> bool:
        """Mark an open alert as resolved."""
        from datetime import datetime, timezone
        with self._lock:
            alert = self._open.pop(fingerprint, None)
        if alert:
            alert.status = AlertStatus.RESOLVED.value
            alert.resolved_at = datetime.now(timezone.utc).isoformat()
            _LOG.info("Alert resolved: %s — %s", fingerprint, reason)
            return True
        return False

    def suppress_until(self, fingerprint: str, seconds: float) -> None:
        """Suppress an alert fingerprint for *seconds* seconds."""
        with self._lock:
            self._last_fired[fingerprint] = time.monotonic() + seconds - self._cooldown

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def add_handler(self, handler: AlertHandler, level: str = "*") -> None:
        """Register a handler for alerts at or above *level*.

        Args:
            handler: Callable that receives an ``AlertEvent``.
            level:   One of INFO/WARNING/ERROR/CRITICAL or ``"*"`` for all.
        """
        with self._lock:
            target = level if level in self._handlers else "*"
            self._handlers[target].append(handler)

    def remove_handler(self, handler: AlertHandler) -> None:
        with self._lock:
            for handlers in self._handlers.values():
                if handler in handlers:
                    handlers.remove(handler)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def open_alerts(self, level: Optional[str] = None) -> list[AlertEvent]:
        with self._lock:
            alerts = list(self._open.values())
        if level:
            alerts = [a for a in alerts if a.level == level]
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    def recent_alerts(self, n: int = 50, level: Optional[str] = None) -> list[AlertEvent]:
        with self._lock:
            alerts = list(reversed(list(self._history)))
        if level:
            alerts = [a for a in alerts if a.level == level]
        return alerts[:n]

    def critical_count(self) -> int:
        with self._lock:
            return sum(1 for a in self._open.values() if a.is_critical)

    @property
    def alert_count(self) -> int:
        return self._alert_count

    @property
    def open_count(self) -> int:
        with self._lock:
            return len(self._open)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _collect_handlers(self, level: str) -> list[AlertHandler]:
        """Collect handlers for *level* — handlers for that exact level plus wildcards."""
        handlers: list[AlertHandler] = list(self._handlers.get("*", []))
        if level in self._handlers:
            handlers.extend(self._handlers[level])
        return handlers

    def _route(self, alert: AlertEvent, handlers: list[AlertHandler]) -> None:
        log_fn = {
            AlertLevel.CRITICAL.value: _LOG.critical,
            AlertLevel.ERROR.value: _LOG.error,
            AlertLevel.WARNING.value: _LOG.warning,
        }.get(alert.level, _LOG.info)

        log_fn("ALERT [%s] %s: %s", alert.level, alert.title, alert.message)

        for handler in handlers:
            try:
                handler(alert)
            except Exception as exc:
                _LOG.error("Alert handler raised: %s", exc)


def get_alert_manager() -> AlertManager:
    """Return (or create) the global ``AlertManager`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = AlertManager()
        return _instance


def _reset_alert_manager() -> None:
    global _instance
    with _instance_lock:
        _instance = None
