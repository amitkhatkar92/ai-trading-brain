"""
iios.ai.model_management.events
==================================
Domain events for A2 Model Management.
"""
from __future__ import annotations

from .event_bus    import ModelEventBus
from .event_types  import ModelEventType
from .model_events import (
    FailoverTriggeredEvent,
    HealthCheckFailedEvent,
    HealthCheckPassedEvent,
    ModelDisabledEvent,
    ModelEnabledEvent,
    ModelEvent,
    ModelHealthChangedEvent,
    ModelRegisteredEvent,
    ModelRemovedEvent,
    RoutingCompletedEvent,
    VersionActivatedEvent,
)

__all__ = [
    "ModelEventBus",
    "ModelEventType",
    "ModelEvent",
    "ModelRegisteredEvent",
    "ModelRemovedEvent",
    "ModelEnabledEvent",
    "ModelDisabledEvent",
    "ModelHealthChangedEvent",
    "RoutingCompletedEvent",
    "FailoverTriggeredEvent",
    "VersionActivatedEvent",
    "HealthCheckPassedEvent",
    "HealthCheckFailedEvent",
]
