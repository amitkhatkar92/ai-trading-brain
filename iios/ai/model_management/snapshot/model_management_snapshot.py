"""
model_management_snapshot.py -- iios.ai.model_management.snapshot
===================================================================
:class:`ModelManagementSnapshot` — immutable point-in-time capture of
the A2 module's state.  Used for dashboards, audits, and health endpoints.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Optional

from ..events.event_bus         import ModelEventBus
from ..health.health_monitor    import HealthMonitor
from ..registry.model_registry  import AIModelRegistry


@dataclass(frozen=True)
class ModelManagementSnapshot:
    """Immutable snapshot of the A2 Model Management module's state."""
    snapshot_id:          str
    captured_at:          float
    model_count:          int
    enabled_model_count:  int
    healthy_model_count:  int
    total_versions:       int
    events_published:     int

    @property
    def taken_at(self) -> float:  # pragma: no cover  # deprecated alias
        """Deprecated: use captured_at."""
        return self.captured_at

    @classmethod
    def capture(
        cls,
        registry:       AIModelRegistry,
        health_monitor: HealthMonitor,
        event_bus:      Optional[ModelEventBus] = None,
    ) -> "ModelManagementSnapshot":
        models = registry.list_all()
        return cls(
            snapshot_id         = str(uuid.uuid4()),
            captured_at         = time.time(),
            model_count         = len(models),
            enabled_model_count = sum(1 for m in models if m.enabled),
            healthy_model_count = sum(
                1 for m in models if health_monitor.is_healthy(m.model_id)
            ),
            total_versions      = sum(len(m.history()) for m in models),
            events_published    = event_bus.published_count if event_bus else 0,
        )
