"""
iios/observation/models/observation_record.py
==============================================
ObservationRecord — extended envelope that wraps an Observation with
processing history, audit events, and derived outputs.

While ``Observation`` is the mutable live entity, ``ObservationRecord``
is the durable, append-only log entry persisted by the storage layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    OBSERVATION_SCHEMA_VERSION,
    SYSTEM_OBSERVER,
    ObservationStatus,
    LifecycleEvent,
    PipelineStage,
)
from .observation import Observation

__all__ = ["ObservationRecord", "ProcessingEvent"]


@dataclass
class ProcessingEvent:
    """A single step recorded in the observation processing history."""

    stage:      PipelineStage
    status:     ObservationStatus
    actor:      str            = SYSTEM_OBSERVER
    timestamp:  float          = field(default_factory=time.time)
    duration_ms: float         = 0.0
    message:    str            = ""
    details:    dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage":       self.stage.value,
            "status":      self.status.value,
            "actor":       self.actor,
            "timestamp":   self.timestamp,
            "duration_ms": self.duration_ms,
            "message":     self.message,
            "details":     dict(self.details),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProcessingEvent":
        return cls(
            stage      = PipelineStage(d.get("stage", PipelineStage.INGEST.value)),
            status     = ObservationStatus(d.get("status", ObservationStatus.CREATED.value)),
            actor      = d.get("actor",       SYSTEM_OBSERVER),
            timestamp  = d.get("timestamp",   time.time()),
            duration_ms= d.get("duration_ms", 0.0),
            message    = d.get("message",     ""),
            details    = dict(d.get("details", {})),
        )


@dataclass
class ObservationRecord:
    """Durable record wrapping an Observation with full processing audit.

    Created once per observation and updated as it moves through the
    pipeline.  The ``history`` list provides a full trace.
    """

    # The observation this record wraps
    observation: Observation

    # Processing history (append-only; ordered by timestamp)
    history:     list[ProcessingEvent] = field(default_factory=list)

    # Lifecycle events emitted
    events_emitted: list[str]          = field(default_factory=list)

    # Derived outputs
    knowledge_ids: list[str]           = field(default_factory=list)

    # Record-level metadata
    record_created_at: float           = field(default_factory=time.time)
    record_updated_at: float           = field(default_factory=time.time)
    record_version:    int             = 1

    # Summary metrics
    total_processing_ms: float         = 0.0
    pipeline_passes:     int           = 0
    pipeline_failures:   int           = 0

    schema_version: str                = OBSERVATION_SCHEMA_VERSION

    @property
    def obs_id(self) -> str:
        return self.observation.id

    @property
    def status(self) -> ObservationStatus:
        return self.observation.status

    def add_event(
        self,
        stage:       PipelineStage,
        status:      ObservationStatus,
        actor:       str            = SYSTEM_OBSERVER,
        duration_ms: float          = 0.0,
        message:     str            = "",
        details:     Optional[dict] = None,
    ) -> None:
        evt = ProcessingEvent(
            stage       = stage,
            status      = status,
            actor       = actor,
            duration_ms = duration_ms,
            message     = message,
            details     = dict(details or {}),
        )
        self.history.append(evt)
        self.total_processing_ms  += duration_ms
        self.record_updated_at     = time.time()
        self.record_version       += 1

    def last_event(self) -> Optional[ProcessingEvent]:
        return self.history[-1] if self.history else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation":        self.observation.to_dict(),
            "history":            [e.to_dict() for e in self.history],
            "events_emitted":     list(self.events_emitted),
            "knowledge_ids":      list(self.knowledge_ids),
            "record_created_at":  self.record_created_at,
            "record_updated_at":  self.record_updated_at,
            "record_version":     self.record_version,
            "total_processing_ms":self.total_processing_ms,
            "pipeline_passes":    self.pipeline_passes,
            "pipeline_failures":  self.pipeline_failures,
            "schema_version":     self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ObservationRecord":
        return cls(
            observation         = Observation.from_dict(d["observation"]),
            history             = [ProcessingEvent.from_dict(e) for e in d.get("history", [])],
            events_emitted      = list(d.get("events_emitted",      [])),
            knowledge_ids       = list(d.get("knowledge_ids",       [])),
            record_created_at   = d.get("record_created_at",  time.time()),
            record_updated_at   = d.get("record_updated_at",  time.time()),
            record_version      = d.get("record_version",     1),
            total_processing_ms = d.get("total_processing_ms",0.0),
            pipeline_passes     = d.get("pipeline_passes",    0),
            pipeline_failures   = d.get("pipeline_failures",  0),
            schema_version      = d.get("schema_version",     OBSERVATION_SCHEMA_VERSION),
        )
