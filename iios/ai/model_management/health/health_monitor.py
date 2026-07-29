"""
health_monitor.py -- iios.ai.model_management.health
======================================================
:class:`HealthMonitor` — central health tracking and reporting service.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import threading
from typing import Dict, Optional

from ..events.event_bus   import ModelEventBus
from ..events.model_events import (
    HealthCheckFailedEvent,
    HealthCheckPassedEvent,
    ModelHealthChangedEvent,
)
from .availability_status import AvailabilityStatus
from .health_report       import HealthReport
from .model_health        import ModelHealth

SYSTEM_ID = "iios:ai:model_management:health_monitor"


class HealthMonitor:
    """Tracks health state for all registered AI models."""

    def __init__(self, event_bus: Optional[ModelEventBus] = None) -> None:
        self._health:     Dict[str, ModelHealth] = {}
        self._lock:       threading.RLock         = threading.RLock()
        self._event_bus:  Optional[ModelEventBus] = event_bus

    def _ensure(self, model_id: str) -> ModelHealth:
        with self._lock:
            if model_id not in self._health:
                self._health[model_id] = ModelHealth(model_id)
            return self._health[model_id]

    # ── Health recording ──────────────────────────────────────────────────────

    def record_success(self, model_id: str) -> None:
        """Record a successful operation / health check for *model_id*."""
        mh      = self._ensure(model_id)
        changed = mh.record_success()
        if self._event_bus:
            self._event_bus.publish(HealthCheckPassedEvent.create(SYSTEM_ID, model_id))
            if changed:
                self._event_bus.publish(ModelHealthChangedEvent.create(
                    SYSTEM_ID, model_id, AvailabilityStatus.AVAILABLE.value
                ))

    def record_failure(self, model_id: str) -> None:
        """Record a failed operation / health check for *model_id*."""
        mh      = self._ensure(model_id)
        changed = mh.record_failure()
        report  = mh.to_report()
        if self._event_bus:
            self._event_bus.publish(HealthCheckFailedEvent.create(
                SYSTEM_ID, model_id, report.failure_count
            ))
            if changed:
                self._event_bus.publish(ModelHealthChangedEvent.create(
                    SYSTEM_ID, model_id, report.status.value, report.failure_count
                ))

    # ── Status overrides ──────────────────────────────────────────────────────

    def set_available(self, model_id: str) -> None:
        self._ensure(model_id).force_available()

    def set_unavailable(self, model_id: str) -> None:
        self._ensure(model_id).force_unavailable()

    # ── Reporting ─────────────────────────────────────────────────────────────

    def get_health(self, model_id: str) -> ModelHealth:
        return self._ensure(model_id)

    def get_report(self, model_id: str) -> HealthReport:
        return self._ensure(model_id).to_report()

    def is_healthy(self, model_id: str) -> bool:
        """Returns True for AVAILABLE, DEGRADED, or UNKNOWN (optimistic)."""
        status = self._ensure(model_id).status
        return status in (
            AvailabilityStatus.AVAILABLE,
            AvailabilityStatus.DEGRADED,
            AvailabilityStatus.UNKNOWN,
        )

    def all_reports(self) -> Dict[str, HealthReport]:
        with self._lock:
            return {mid: mh.to_report() for mid, mh in self._health.items()}
