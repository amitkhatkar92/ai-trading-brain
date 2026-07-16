"""iios/execution/oms/persistence/recovery_record.py
==================================================
RecoveryRecord — describes a single persistence recovery operation.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.persistence.constants import RecordType, RecoveryState


@dataclass(frozen=True)
class RecoveryRecord:
    """
    Immutable record describing a recovery attempt.

    A recovery restores a StorageRecord to a known-good state
    from a checkpoint or snapshot.  The `payload` field holds
    the serialised domain object captured at the checkpoint.
    """
    recovery_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:       str   = ""
    record_id:      str   = ""
    record_type:    RecordType    = RecordType.ORDER
    checkpoint_id:  str   = ""     # ID of the checkpoint used as source
    snapshot_id:    str   = ""     # ID of the snapshot used as source (alt)
    recovery_state: RecoveryState = RecoveryState.PENDING
    failure_reason: str   = ""
    payload:        dict[str, Any] = field(default_factory=dict)   # checkpoint data
    metadata:       dict[str, Any] = field(default_factory=dict)
    created_at:     float = field(default_factory=time.time)
    completed_at:   float = 0.0

    @property
    def is_pending(self) -> bool:
        return self.recovery_state == RecoveryState.PENDING

    @property
    def is_in_progress(self) -> bool:
        return self.recovery_state == RecoveryState.IN_PROGRESS

    @property
    def is_complete(self) -> bool:
        return self.recovery_state in (
            RecoveryState.COMPLETED,
            RecoveryState.FAILED,
            RecoveryState.PARTIAL,
        )

    @property
    def is_successful(self) -> bool:
        return self.recovery_state == RecoveryState.COMPLETED

    def with_state(
        self,
        state:          RecoveryState,
        failure_reason: str = "",
    ) -> RecoveryRecord:
        """Return a new RecoveryRecord with updated state."""
        import dataclasses
        completed_at = time.time() if state in (
            RecoveryState.COMPLETED, RecoveryState.FAILED, RecoveryState.PARTIAL
        ) else self.completed_at
        return dataclasses.replace(
            self,
            recovery_state = state,
            failure_reason = failure_reason or self.failure_reason,
            completed_at   = completed_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_id":    self.recovery_id,
            "order_id":       self.order_id,
            "record_id":      self.record_id,
            "record_type":    self.record_type.value,
            "checkpoint_id":  self.checkpoint_id,
            "snapshot_id":    self.snapshot_id,
            "recovery_state": self.recovery_state.value,
            "failure_reason": self.failure_reason,
            "created_at":     self.created_at,
            "completed_at":   self.completed_at,
        }
