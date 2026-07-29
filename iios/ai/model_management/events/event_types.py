"""
event_types.py -- iios.ai.model_management.events
===================================================
:class:`ModelEventType` — enumeration of all A2 domain events.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from enum import Enum


class ModelEventType(str, Enum):
    """All domain events published by the A2 Model Management module."""
    MODEL_REGISTERED    = "model.registered"
    MODEL_REMOVED       = "model.removed"
    MODEL_ENABLED       = "model.enabled"
    MODEL_DISABLED      = "model.disabled"
    MODEL_HEALTH_CHANGED = "model.health_changed"
    ROUTING_COMPLETED   = "routing.completed"
    FAILOVER_TRIGGERED  = "routing.failover_triggered"
    VERSION_ACTIVATED   = "model.version_activated"
    HEALTH_CHECK_PASSED = "health.check_passed"
    HEALTH_CHECK_FAILED = "health.check_failed"
