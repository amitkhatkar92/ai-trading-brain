"""
iios/monitoring/event_logger.py
=================================
Business and lifecycle event logging for IIOS subsystems.

Events are higher-level than log lines — they capture significant state
transitions such as "trade executed", "strategy disabled", "kill-switch
triggered", etc. They are stored in-memory and periodically written to
a JSONL file for later analysis.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from pathlib import Path
from typing import Any, Optional

from .monitoring_constants import EventCategory, AlertLevel
from .monitoring_models import EventRecord

__all__ = [
    "EventLogger",
    "get_event_logger",
]

_LOG = logging.getLogger("iios.monitoring.events")
_instance_lock = threading.Lock()
_instance: Optional["EventLogger"] = None


class EventLogger:
    """Records significant business and lifecycle events.

    Args:
        log_file:       JSONL file path for persistent event log.
        max_in_memory:  Maximum events to keep in memory.
    """

    def __init__(
        self,
        log_file: str = "logs/events.jsonl",
        max_in_memory: int = 5000,
    ) -> None:
        self._log_file = Path(log_file)
        self._lock = threading.Lock()
        self._events: deque[EventRecord] = deque(maxlen=max_in_memory)
        self._event_count: int = 0
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        # Subscribers: event_type → list[callable]
        self._subscribers: dict[str, list[Any]] = {}

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def log(
        self,
        category: str,
        event_type: str,
        description: str,
        component: str = "",
        layer: str = "",
        severity: str = "INFO",
        correlation_id: str = "",
        **data: Any,
    ) -> EventRecord:
        """Record a business event.

        Args:
            category:    ``EventCategory`` value.
            event_type:  Short type identifier (e.g. ``"TRADE_EXECUTED"``).
            description: Human-readable description.
            component:   Source IIOS component.
            layer:       Source IIOS layer.
            severity:    ``AlertLevel`` string.
            **data:      Arbitrary event payload.
        """
        record = EventRecord(
            category=category,
            event_type=event_type,
            description=description,
            component=component,
            layer=layer,
            severity=severity,
            correlation_id=correlation_id,
            data=data,
        )
        self._persist(record)
        self._notify(record)
        return record

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    def trade_executed(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        strategy: str = "",
        paper: bool = True,
        correlation_id: str = "",
        **extra: Any,
    ) -> EventRecord:
        return self.log(
            category=EventCategory.TRADING.value,
            event_type="TRADE_EXECUTED",
            description=f"Trade: {side} {quantity} {symbol} @ {price}",
            component="ExecutionEngine",
            layer="ExecutionEngine",
            severity=AlertLevel.INFO.value,
            correlation_id=correlation_id,
            symbol=symbol, side=side, quantity=quantity, price=price,
            strategy=strategy, paper=paper, **extra,
        )

    def strategy_disabled(
        self,
        strategy_name: str,
        reason: str,
        component: str = "LearningSystem",
        correlation_id: str = "",
    ) -> EventRecord:
        return self.log(
            category=EventCategory.STRATEGY.value,
            event_type="STRATEGY_DISABLED",
            description=f"Strategy disabled: {strategy_name} — {reason}",
            component=component,
            layer=component,
            severity=AlertLevel.WARNING.value,
            correlation_id=correlation_id,
            strategy=strategy_name, reason=reason,
        )

    def kill_switch_triggered(
        self,
        reason: str,
        vix: Optional[float] = None,
        daily_loss_pct: Optional[float] = None,
        correlation_id: str = "",
    ) -> EventRecord:
        return self.log(
            category=EventCategory.RISK.value,
            event_type="KILL_SWITCH_TRIGGERED",
            description=f"Risk kill-switch: {reason}",
            component="RiskGuardian",
            layer="RiskGuardian",
            severity=AlertLevel.CRITICAL.value,
            correlation_id=correlation_id,
            reason=reason, vix=vix, daily_loss_pct=daily_loss_pct,
        )

    def system_phase_changed(
        self,
        old_phase: str,
        new_phase: str,
        component: str = "LifecycleManager",
    ) -> EventRecord:
        return self.log(
            category=EventCategory.LIFECYCLE.value,
            event_type="PHASE_CHANGED",
            description=f"System phase: {old_phase} → {new_phase}",
            component=component,
            severity=AlertLevel.INFO.value,
            old_phase=old_phase, new_phase=new_phase,
        )

    def config_reloaded(
        self,
        changed_keys: list[str],
        version: int,
        component: str = "ConfigurationManager",
    ) -> EventRecord:
        return self.log(
            category=EventCategory.CONFIG.value,
            event_type="CONFIG_RELOADED",
            description=f"Configuration reloaded (v{version}): {len(changed_keys)} key(s) changed",
            component=component,
            severity=AlertLevel.INFO.value,
            changed_keys=changed_keys, version=version,
        )

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(self, event_type: str, callback: Any) -> None:
        """Register a callback for a specific event type or ``"*"`` for all."""
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback: Any) -> None:
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    c for c in self._subscribers[event_type] if c is not callback
                ]

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def recent(self, n: int = 50, event_type: Optional[str] = None) -> list[EventRecord]:
        """Return up to *n* most-recent events, optionally filtered by type."""
        with self._lock:
            events = list(reversed(list(self._events)))
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[:n]

    def since(self, category: str, limit: int = 100) -> list[EventRecord]:
        """Return events for a given category."""
        with self._lock:
            events = [e for e in reversed(list(self._events)) if e.category == category]
        return events[:limit]

    @property
    def event_count(self) -> int:
        return self._event_count

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _persist(self, record: EventRecord) -> None:
        line = json.dumps({
            "event_id": record.event_id,
            "timestamp": record.timestamp,
            "category": record.category,
            "event_type": record.event_type,
            "description": record.description,
            "component": record.component,
            "layer": record.layer,
            "severity": record.severity,
            "correlation_id": record.correlation_id,
            "data": record.data,
        }, default=str)

        with self._lock:
            self._events.append(record)
            self._event_count += 1
            try:
                with self._log_file.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError as exc:
                _LOG.error("Event log write failed: %s", exc)

    def _notify(self, record: EventRecord) -> None:
        with self._lock:
            specific = list(self._subscribers.get(record.event_type, []))
            wildcard = list(self._subscribers.get("*", []))

        for cb in specific + wildcard:
            try:
                cb(record)
            except Exception as exc:
                _LOG.warning("Event subscriber error for %s: %s", record.event_type, exc)


def get_event_logger(log_file: str = "logs/events.jsonl") -> EventLogger:
    """Return (or create) the global ``EventLogger`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = EventLogger(log_file=log_file)
        return _instance


def _reset_event_logger() -> None:
    global _instance
    with _instance_lock:
        _instance = None
