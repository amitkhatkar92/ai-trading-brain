"""iios/execution/engine/execution_statistics.py
==================================================
ExecutionStatistics — per-execution metrics.
EngineStatistics    — aggregate metrics across all executions.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

from .execution_state import EngineExecutionState


@dataclass
class ExecutionStatistics:
    """
    Metrics for a single execution run.

    Updated by the registry as the execution advances through states.

    Attributes
    ----------
    execution_id         : Owning execution session.
    created_at           : When the execution record was created.
    started_at           : When the engine began processing (IDLE → VALIDATING).
    validating_at        : Timestamp of VALIDATING entry.
    preparing_at         : Timestamp of PREPARING entry.
    ready_at             : Timestamp of READY entry.
    executing_at         : Timestamp of EXECUTING entry.
    completed_at         : Timestamp of terminal state entry.
    validation_duration  : Seconds in VALIDATING.
    preparation_duration : Seconds in PREPARING.
    execution_duration   : Seconds in EXECUTING (plus WAITING).
    total_duration       : Total wall-clock time from started_at to completed_at.
    succeeded            : True if final state is COMPLETED.
    final_state          : Terminal engine state (or None if not finished).
    """

    execution_id: str   = ""
    created_at:   float = field(default_factory=time.time)

    # ── Phase timestamps ───────────────────────────────────────────────────────
    started_at:   Optional[float] = None
    validating_at: Optional[float] = None
    preparing_at:  Optional[float] = None
    ready_at:      Optional[float] = None
    executing_at:  Optional[float] = None
    completed_at:  Optional[float] = None

    # ── Phase durations (seconds) ──────────────────────────────────────────────
    validation_duration:  Optional[float] = None
    preparation_duration: Optional[float] = None
    execution_duration:   Optional[float] = None

    # ── Outcome ────────────────────────────────────────────────────────────────
    succeeded:   bool                         = False
    final_state: Optional[EngineExecutionState] = None

    # ── Internal tracking ─────────────────────────────────────────────────────
    _state_durations:    dict[str, float]                      = field(default_factory=dict, repr=False)
    _current_state_entry: Optional[Tuple[EngineExecutionState, float]] = field(default=None, repr=False)
    _lock:               threading.Lock                         = field(default_factory=threading.Lock, repr=False)

    def on_transition(
        self,
        from_state:  EngineExecutionState,
        to_state:    EngineExecutionState,
        occurred_at: Optional[float] = None,
    ) -> None:
        """Update statistics when the execution transitions between states."""
        now = occurred_at if occurred_at is not None else time.time()
        with self._lock:
            # Close duration for the outgoing state
            if self._current_state_entry is not None:
                prev_state, entry_time = self._current_state_entry
                self._state_durations[prev_state.value] = (
                    self._state_durations.get(prev_state.value, 0.0)
                    + (now - entry_time)
                )
            # Open duration for incoming state
            self._current_state_entry = (to_state, now)

            # Phase timestamps
            if to_state == EngineExecutionState.VALIDATING:
                self.started_at   = now
                self.validating_at = now
            elif to_state == EngineExecutionState.PREPARING:
                self.preparing_at = now
                if self.validating_at is not None:
                    self.validation_duration = now - self.validating_at
            elif to_state == EngineExecutionState.READY:
                self.ready_at = now
                if self.preparing_at is not None:
                    self.preparation_duration = now - self.preparing_at
            elif to_state == EngineExecutionState.EXECUTING:
                self.executing_at = now
            elif to_state in (EngineExecutionState.COMPLETED,
                              EngineExecutionState.FAILED,
                              EngineExecutionState.CANCELLED):
                self.completed_at = now
                self.final_state  = to_state
                self.succeeded    = to_state == EngineExecutionState.COMPLETED
                if self.executing_at is not None:
                    self.execution_duration = now - self.executing_at

    @property
    def total_duration(self) -> Optional[float]:
        """Wall-clock time from started_at to completed_at (or now if running)."""
        if self.started_at is None:
            return None
        end = self.completed_at if self.completed_at is not None else time.time()
        return end - self.started_at

    @property
    def state_durations(self) -> dict[str, float]:
        """
        Seconds spent in each completed state.
        The current open state's running duration is excluded (see to_dict for live value).
        """
        with self._lock:
            return dict(self._state_durations)

    def to_dict(self) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            durations = dict(self._state_durations)
            # Include the current open state's live duration
            if self._current_state_entry is not None:
                open_state, entry_time = self._current_state_entry
                key = open_state.value
                durations[key] = durations.get(key, 0.0) + (now - entry_time)

        return {
            "execution_id":        self.execution_id,
            "created_at":          self.created_at,
            "started_at":          self.started_at,
            "completed_at":        self.completed_at,
            "total_duration_sec":  round(self.total_duration or 0.0, 4),
            "validation_duration": self.validation_duration,
            "preparation_duration": self.preparation_duration,
            "execution_duration":  self.execution_duration,
            "succeeded":           self.succeeded,
            "final_state":         self.final_state.value if self.final_state else None,
            "state_durations":     {k: round(v, 4) for k, v in durations.items()},
        }


@dataclass
class EngineStatistics:
    """
    Aggregate statistics across all executions managed by the engine.

    Updated by ExecutionRegistry on each completion.

    Attributes
    ----------
    execution_count      : Total executions registered.
    success_count        : Executions that reached COMPLETED.
    failure_count        : Executions that reached FAILED.
    cancellation_count   : Executions that reached CANCELLED.
    total_duration_ms    : Sum of all individual durations (ms).
    total_validation_ms  : Sum of all validation durations (ms).
    total_preparation_ms : Sum of all preparation durations (ms).
    total_execution_ms   : Sum of all execution-phase durations (ms).
    """

    execution_count:     int   = 0
    success_count:       int   = 0
    failure_count:       int   = 0
    cancellation_count:  int   = 0
    total_duration_ms:   float = 0.0
    total_validation_ms: float = 0.0
    total_preparation_ms: float = 0.0
    total_execution_ms:  float = 0.0

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_completion(self, stats: ExecutionStatistics) -> None:
        """Incorporate a completed execution's statistics."""
        with self._lock:
            self.execution_count += 1
            if stats.succeeded:
                self.success_count += 1
            elif stats.final_state == EngineExecutionState.CANCELLED:
                self.cancellation_count += 1
            else:
                self.failure_count += 1

            dur = stats.total_duration
            if dur is not None:
                self.total_duration_ms += dur * 1_000
            if stats.validation_duration is not None:
                self.total_validation_ms += stats.validation_duration * 1_000
            if stats.preparation_duration is not None:
                self.total_preparation_ms += stats.preparation_duration * 1_000
            if stats.execution_duration is not None:
                self.total_execution_ms += stats.execution_duration * 1_000

    @property
    def success_rate(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    @property
    def failure_rate(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.failure_count / self.execution_count

    @property
    def avg_execution_time_ms(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.total_duration_ms / self.execution_count

    @property
    def avg_preparation_time_ms(self) -> float:
        n = self.success_count + self.failure_count + self.cancellation_count
        if n == 0:
            return 0.0
        return self.total_preparation_ms / n

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "execution_count":     self.execution_count,
                "success_count":       self.success_count,
                "failure_count":       self.failure_count,
                "cancellation_count":  self.cancellation_count,
                "success_rate":        round(self.success_rate, 4),
                "failure_rate":        round(self.failure_rate, 4),
                "avg_execution_time_ms":  round(self.avg_execution_time_ms, 3),
                "avg_preparation_time_ms": round(self.avg_preparation_time_ms, 3),
                "total_duration_ms":   round(self.total_duration_ms, 3),
                "total_validation_ms": round(self.total_validation_ms, 3),
                "total_preparation_ms": round(self.total_preparation_ms, 3),
                "total_execution_ms":  round(self.total_execution_ms, 3),
            }
