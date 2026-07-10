"""iios/integration/research/tracking/execution_tracker.py

Tracks per-session execution progress, checkpoints, and timing.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.research_constants  import CheckpointStatus
from iios.integration.research.research_exceptions import (
    CheckpointError,
    TrackingSessionNotFoundError,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionCheckpoint:
    """Saved state for a partially-completed experiment session."""
    checkpoint_id: str            = field(default_factory=lambda: str(uuid.uuid4()))
    session_id:    str            = ""
    step:          int            = 0
    total_steps:   int            = 0
    data:          dict[str, Any] = field(default_factory=dict)
    status:        CheckpointStatus = CheckpointStatus.SAVED
    saved_at:      float          = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id":    self.session_id,
            "step":          self.step,
            "total_steps":   self.total_steps,
            "status":        self.status.value,
            "saved_at":      self.saved_at,
        }


@dataclass
class _TrackingRecord:
    session_id:   str
    started_at:   float = field(default_factory=time.time)
    ended_at:     float | None = None
    step:         int = 0
    total_steps:  int = 0
    checkpoints:  list[ExecutionCheckpoint] = field(default_factory=list)


class ExecutionTracker:
    """
    Tracks execution progress and checkpoints for experiment sessions.
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._records: dict[str, _TrackingRecord] = {}
        self._stats: dict[str, int] = {
            "sessions_tracked": 0,
            "checkpoints_saved": 0,
            "checkpoints_restored": 0,
        }

    def start_tracking(self, session_id: str, total_steps: int = 0) -> None:
        with self._lock:
            self._records[session_id] = _TrackingRecord(
                session_id  = session_id,
                total_steps = total_steps,
            )
            self._stats["sessions_tracked"] += 1
        logger.debug("[ExecutionTracker] Started tracking session '%s'.", session_id)

    def update_progress(
        self,
        session_id: str,
        step:       int,
        data:       dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            rec = self._records.get(session_id)
            if rec is None:
                raise TrackingSessionNotFoundError(f"Session '{session_id}' not tracked.")
            rec.step = step

    def save_checkpoint(
        self,
        session_id: str,
        data:       dict[str, Any] | None = None,
    ) -> ExecutionCheckpoint:
        with self._lock:
            rec = self._records.get(session_id)
            if rec is None:
                raise TrackingSessionNotFoundError(f"Session '{session_id}' not tracked.")
            ckpt = ExecutionCheckpoint(
                session_id  = session_id,
                step        = rec.step,
                total_steps = rec.total_steps,
                data        = data or {},
            )
            rec.checkpoints.append(ckpt)
            self._stats["checkpoints_saved"] += 1
        logger.debug(
            "[ExecutionTracker] Checkpoint '%s' saved (step=%d).",
            ckpt.checkpoint_id, ckpt.step,
        )
        return ckpt

    def restore_checkpoint(self, session_id: str) -> ExecutionCheckpoint | None:
        """Return the most recent checkpoint for a session, or None."""
        with self._lock:
            rec = self._records.get(session_id)
            if rec is None or not rec.checkpoints:
                return None
            ckpt = rec.checkpoints[-1]
            ckpt.status = CheckpointStatus.RESTORED
            self._stats["checkpoints_restored"] += 1
        return ckpt

    def finish(self, session_id: str) -> None:
        with self._lock:
            rec = self._records.get(session_id)
            if rec:
                rec.ended_at = time.time()

    def get_progress(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._records.get(session_id)
            if rec is None:
                raise TrackingSessionNotFoundError(f"Session '{session_id}' not tracked.")
            pct = (rec.step / rec.total_steps * 100) if rec.total_steps > 0 else 0.0
            return {
                "session_id":  session_id,
                "step":        rec.step,
                "total_steps": rec.total_steps,
                "progress_pct": pct,
            }

    def elapsed_sec(self, session_id: str) -> float:
        with self._lock:
            rec = self._records.get(session_id)
            if rec is None:
                return 0.0
            end = rec.ended_at or time.time()
            return end - rec.started_at

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._stats)
