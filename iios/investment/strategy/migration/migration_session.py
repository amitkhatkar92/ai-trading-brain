"""iios/investment/strategy/migration/migration_session.py
Per-strategy migration state machine with rollback checkpoint support.
"""
from __future__ import annotations

import threading
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.migration_status import (
    MigrationPhase,
    MigrationStatus,
    RollbackReason,
)
from iios.investment.strategy.migration.migration_steps import MigrationStepResult, StepResult
from iios.investment.strategy.migration.legacy_metadata import LegacyStrategyMetadata
from iios.investment.strategy.migration.strategy_adapter import LegacyStrategyAdapter
from iios.investment.strategy.migration.validation_report import ValidationReport


@dataclass
class MigrationSession:
    """
    Complete state for one strategy's migration journey.

    Thread-safe. Supports rollback to the last saved checkpoint.
    """

    session_id:    str
    strategy_id:   str
    strategy_name: str

    metadata: LegacyStrategyMetadata
    status:   MigrationStatus = field(default=MigrationStatus.NOT_STARTED)

    adapter:           Optional[LegacyStrategyAdapter] = field(default=None)
    validation_report: Optional[ValidationReport]      = field(default=None)
    step_results:      List[MigrationStepResult]       = field(default_factory=list)

    # Checkpoint for rollback
    _checkpoint:       Dict[str, Any]                  = field(default_factory=dict)
    _pre_rollback_status: Optional[MigrationStatus]    = field(default=None)

    # Timestamps
    started_at:    datetime                = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at:  Optional[datetime]      = field(default=None)
    rolled_back_at: Optional[datetime]     = field(default=None)

    # Annotations
    notes:  List[str]          = field(default_factory=list)
    error:  Optional[str]      = field(default=None)

    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False, compare=False)

    @classmethod
    def create(
        cls,
        metadata:   LegacyStrategyMetadata,
        session_id: Optional[str] = None,
    ) -> "MigrationSession":
        return cls(
            session_id=session_id or str(uuid.uuid4()),
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            metadata=metadata,
        )

    # ── Status transitions ────────────────────────────────────────────────────

    def advance(self, status: MigrationStatus, note: Optional[str] = None) -> None:
        with self._lock:
            self.status = status
            if note:
                self.notes.append(note)
            if status.is_terminal:
                self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: str) -> None:
        with self._lock:
            self.error  = reason
            self.status = MigrationStatus.FAILED
            self.completed_at = datetime.now(timezone.utc)

    # ── Steps ─────────────────────────────────────────────────────────────────

    def add_step(self, result: MigrationStepResult) -> None:
        with self._lock:
            self.step_results.append(result)

    def last_step(self) -> Optional[MigrationStepResult]:
        with self._lock:
            return self.step_results[-1] if self.step_results else None

    def steps_passed(self) -> bool:
        with self._lock:
            return all(s.is_success for s in self.step_results)

    # ── Checkpoint / rollback ─────────────────────────────────────────────────

    def save_checkpoint(self) -> None:
        """Snapshot current state for rollback."""
        with self._lock:
            self._checkpoint = {
                "status":           self.status,
                "adapter":          self.adapter,
                "validation_report": self.validation_report,
                "step_results":     list(self.step_results),
                "notes":            list(self.notes),
                "error":            self.error,
                "saved_at":         datetime.now(timezone.utc).isoformat(),
            }

    def rollback(self, reason: RollbackReason = RollbackReason.MANUAL_REQUEST) -> bool:
        """Restore from checkpoint if available. Returns True on success."""
        with self._lock:
            if not self._checkpoint:
                return False
            self._pre_rollback_status = self.status
            self.status            = MigrationStatus.ROLLED_BACK
            self.adapter           = self._checkpoint.get("adapter")
            self.validation_report = self._checkpoint.get("validation_report")
            self.step_results      = list(self._checkpoint.get("step_results", []))
            self.notes             = list(self._checkpoint.get("notes", []))
            self.error             = self._checkpoint.get("error")
            self.notes.append(f"[rollback] reason={reason.value}")
            self.rolled_back_at    = datetime.now(timezone.utc)
            return True

    def has_checkpoint(self) -> bool:
        with self._lock:
            return bool(self._checkpoint)

    # ── Result accessors ──────────────────────────────────────────────────────

    @property
    def is_complete(self) -> bool:
        return self.status.is_terminal

    @property
    def is_successful(self) -> bool:
        return self.status == MigrationStatus.COMPLETED

    @property
    def duration_ms(self) -> float:
        end = self.completed_at or datetime.now(timezone.utc)
        delta = end - self.started_at
        return round(delta.total_seconds() * 1000, 2)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id":    self.session_id,
                "strategy_id":   self.strategy_id,
                "strategy_name": self.strategy_name,
                "status":        self.status.value,
                "error":         self.error,
                "started_at":    self.started_at.isoformat(),
                "completed_at":  self.completed_at.isoformat() if self.completed_at else None,
                "duration_ms":   self.duration_ms,
                "step_count":    len(self.step_results),
                "steps_passed":  self.steps_passed(),
                "notes":         list(self.notes),
                "has_adapter":   self.adapter is not None,
                "has_report":    self.validation_report is not None,
            }
