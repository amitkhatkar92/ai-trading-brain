"""
model_events.py -- iios.ai.model_management.events
====================================================
Immutable domain events for the A2 Model Management module.

All events are frozen dataclasses — they are safe to pass across threads,
cache, and replay.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple

from .event_types import ModelEventType


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelEvent:
    """Base class for all A2 domain events."""
    event_id:   str
    event_type: ModelEventType
    source:     str
    occurred_at: float

    def _base_kwargs(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type,
            "source":      self.source,
            "occurred_at": self.occurred_at,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "source":      self.source,
            "occurred_at": self.occurred_at,
        }


# ---------------------------------------------------------------------------
# Typed events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelRegisteredEvent(ModelEvent):
    model_id:   str = ""
    model_name: str = ""

    @classmethod
    def create(cls, source: str, model_id: str, model_name: str) -> "ModelRegisteredEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.MODEL_REGISTERED,
            source=source, occurred_at=time.time(),
            model_id=model_id, model_name=model_name,
        )


@dataclass(frozen=True)
class ModelRemovedEvent(ModelEvent):
    model_id:   str = ""
    model_name: str = ""

    @classmethod
    def create(cls, source: str, model_id: str, model_name: str) -> "ModelRemovedEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.MODEL_REMOVED,
            source=source, occurred_at=time.time(),
            model_id=model_id, model_name=model_name,
        )


@dataclass(frozen=True)
class ModelEnabledEvent(ModelEvent):
    model_id: str = ""

    @classmethod
    def create(cls, source: str, model_id: str) -> "ModelEnabledEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.MODEL_ENABLED,
            source=source, occurred_at=time.time(),
            model_id=model_id,
        )


@dataclass(frozen=True)
class ModelDisabledEvent(ModelEvent):
    model_id: str = ""

    @classmethod
    def create(cls, source: str, model_id: str) -> "ModelDisabledEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.MODEL_DISABLED,
            source=source, occurred_at=time.time(),
            model_id=model_id,
        )


@dataclass(frozen=True)
class ModelHealthChangedEvent(ModelEvent):
    model_id:       str = ""
    new_status:     str = ""
    failure_count:  int = 0

    @classmethod
    def create(cls, source: str, model_id: str, new_status: str, failure_count: int = 0) -> "ModelHealthChangedEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.MODEL_HEALTH_CHANGED,
            source=source, occurred_at=time.time(),
            model_id=model_id, new_status=new_status, failure_count=failure_count,
        )


@dataclass(frozen=True)
class RoutingCompletedEvent(ModelEvent):
    selected_model_id:   str   = ""
    strategy_used:       str   = ""
    score:               float = 0.0
    alternatives_count:  int   = 0

    @classmethod
    def create(cls, source: str, selected_model_id: str, strategy_used: str,
               score: float = 1.0, alternatives_count: int = 0) -> "RoutingCompletedEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.ROUTING_COMPLETED,
            source=source, occurred_at=time.time(),
            selected_model_id=selected_model_id, strategy_used=strategy_used,
            score=score, alternatives_count=alternatives_count,
        )


@dataclass(frozen=True)
class FailoverTriggeredEvent(ModelEvent):
    failed_model_id:   str = ""
    fallback_model_id: str = ""

    @classmethod
    def create(cls, source: str, failed_model_id: str, fallback_model_id: str) -> "FailoverTriggeredEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.FAILOVER_TRIGGERED,
            source=source, occurred_at=time.time(),
            failed_model_id=failed_model_id, fallback_model_id=fallback_model_id,
        )


@dataclass(frozen=True)
class VersionActivatedEvent(ModelEvent):
    model_id:   str = ""
    version_id: str = ""
    version_number: int = 0

    @classmethod
    def create(cls, source: str, model_id: str, version_id: str, version_number: int) -> "VersionActivatedEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.VERSION_ACTIVATED,
            source=source, occurred_at=time.time(),
            model_id=model_id, version_id=version_id, version_number=version_number,
        )


@dataclass(frozen=True)
class HealthCheckPassedEvent(ModelEvent):
    model_id: str = ""

    @classmethod
    def create(cls, source: str, model_id: str) -> "HealthCheckPassedEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.HEALTH_CHECK_PASSED,
            source=source, occurred_at=time.time(),
            model_id=model_id,
        )


@dataclass(frozen=True)
class HealthCheckFailedEvent(ModelEvent):
    model_id:      str = ""
    failure_count: int = 0

    @classmethod
    def create(cls, source: str, model_id: str, failure_count: int = 0) -> "HealthCheckFailedEvent":
        return cls(
            event_id=str(uuid.uuid4()), event_type=ModelEventType.HEALTH_CHECK_FAILED,
            source=source, occurred_at=time.time(),
            model_id=model_id, failure_count=failure_count,
        )
