"""iios/execution/oms/persistence/repository_events.py
==================================================
PersistenceEvent and factory functions for all persistence domain events.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.persistence.constants import PersistenceEventType


@dataclass(frozen=True)
class PersistenceEvent:
    """
    Immutable domain event emitted by the persistence layer.

    Events are append-only and capture every significant state change.
    """
    event_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:     PersistenceEventType = PersistenceEventType.RECORD_SAVED
    record_id:      str   = ""
    repository_id:  str   = ""
    record_version: int   = 0
    recovery_id:    str   = ""
    occurred_at:    float = field(default_factory=time.time)
    succeeded:      bool  = True
    detail:         str   = ""
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "record_id":      self.record_id,
            "repository_id":  self.repository_id,
            "record_version": self.record_version,
            "recovery_id":    self.recovery_id,
            "occurred_at":    self.occurred_at,
            "succeeded":      self.succeeded,
            "detail":         self.detail,
        }


# ---------------------------------------------------------------------------
# Factory functions — one per event type
# ---------------------------------------------------------------------------

def make_record_saved(
    record_id:      str,
    repository_id:  str,
    version:        int,
    correlation_id: str = "",
) -> PersistenceEvent:
    return PersistenceEvent(
        event_type     = PersistenceEventType.RECORD_SAVED,
        record_id      = record_id,
        repository_id  = repository_id,
        record_version = version,
        detail         = f"Saved version={version}",
        metadata       = {"correlation_id": correlation_id} if correlation_id else {},
    )


def make_record_updated(
    record_id:      str,
    repository_id:  str,
    version:        int,
    correlation_id: str = "",
) -> PersistenceEvent:
    return PersistenceEvent(
        event_type     = PersistenceEventType.RECORD_UPDATED,
        record_id      = record_id,
        repository_id  = repository_id,
        record_version = version,
        detail         = f"Updated to version={version}",
        metadata       = {"correlation_id": correlation_id} if correlation_id else {},
    )


def make_record_archived(
    record_id:     str,
    repository_id: str,
    version:       int = 0,
) -> PersistenceEvent:
    return PersistenceEvent(
        event_type    = PersistenceEventType.RECORD_ARCHIVED,
        record_id     = record_id,
        repository_id = repository_id,
        record_version = version,
        detail        = "Record archived",
    )


def make_record_restored(
    record_id:     str,
    repository_id: str,
    version:       int = 0,
) -> PersistenceEvent:
    return PersistenceEvent(
        event_type    = PersistenceEventType.RECORD_RESTORED,
        record_id     = record_id,
        repository_id = repository_id,
        record_version = version,
        detail        = "Record restored from archive",
    )


def make_recovery_started(
    record_id:   str,
    recovery_id: str,
    repository_id: str = "",
) -> PersistenceEvent:
    return PersistenceEvent(
        event_type    = PersistenceEventType.RECOVERY_STARTED,
        record_id     = record_id,
        repository_id = repository_id,
        recovery_id   = recovery_id,
        detail        = f"Recovery {recovery_id} started",
    )


def make_recovery_completed(
    record_id:   str,
    recovery_id: str,
    succeeded:   bool,
    repository_id: str = "",
) -> PersistenceEvent:
    return PersistenceEvent(
        event_type    = PersistenceEventType.RECOVERY_COMPLETED,
        record_id     = record_id,
        repository_id = repository_id,
        recovery_id   = recovery_id,
        succeeded     = succeeded,
        detail        = f"Recovery {recovery_id} {'completed' if succeeded else 'failed'}",
    )


def make_repository_validated(
    repository_id: str,
    is_valid:      bool,
    detail:        str = "",
) -> PersistenceEvent:
    return PersistenceEvent(
        event_type    = PersistenceEventType.REPOSITORY_VALIDATED,
        repository_id = repository_id,
        succeeded     = is_valid,
        detail        = detail or ("Validation passed" if is_valid else "Validation failed"),
    )
