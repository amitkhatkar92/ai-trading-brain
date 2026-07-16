"""iios/execution/engine/execution_result.py
==================================================
ExecutionResult — the final outcome record returned by ExecutionEngine.submit().

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .execution_state import EngineExecutionState


@dataclass
class ExecutionResult:
    """
    Immutable outcome record produced at the end of one execution run.

    Returned by ExecutionEngine.submit().
    Stored in ExecutionRegistry alongside the execution record.

    Attributes
    ----------
    result_id        : Unique result identifier.
    execution_id     : Parent execution session.
    request_id       : The originating request.
    order_id         : Order that was processed.
    final_state      : Terminal engine state (COMPLETED / FAILED / CANCELLED).
    succeeded        : True iff final_state == COMPLETED.
    validation_errors: Non-empty when validation caused failure.
    error_message    : Human-readable failure description (empty on success).
    error_code       : Machine-readable failure code (empty on success).
    snapshot_id      : ID of the associated ExecutionSnapshot (if published).
    started_at       : Unix timestamp when processing began.
    completed_at     : Unix timestamp when processing finished.
    duration_ms      : Wall-clock time from start to finish in milliseconds.
    metadata         : Arbitrary extra payload.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    result_id:    str = field(default_factory=lambda: f"RES-{uuid.uuid4().hex[:16].upper()}")
    execution_id: str = ""
    request_id:   str = ""
    order_id:     str = ""

    # ── Outcome ───────────────────────────────────────────────────────────────
    final_state:       EngineExecutionState = EngineExecutionState.COMPLETED
    succeeded:         bool                 = True
    validation_errors: tuple[str, ...]      = field(default_factory=tuple)
    error_message:     str                  = ""
    error_code:        str                  = ""

    # ── Snapshot reference ────────────────────────────────────────────────────
    snapshot_id: str = ""

    # ── Timing ────────────────────────────────────────────────────────────────
    started_at:   float = field(default_factory=time.time)
    completed_at: float = field(default_factory=time.time)
    duration_ms:  float = 0.0

    # ── Extra ─────────────────────────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def failed(self) -> bool:
        return self.final_state == EngineExecutionState.FAILED

    @property
    def cancelled(self) -> bool:
        return self.final_state == EngineExecutionState.CANCELLED

    @property
    def has_errors(self) -> bool:
        return bool(self.validation_errors) or bool(self.error_message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":         self.result_id,
            "execution_id":      self.execution_id,
            "request_id":        self.request_id,
            "order_id":          self.order_id,
            "final_state":       self.final_state.value,
            "succeeded":         self.succeeded,
            "validation_errors": list(self.validation_errors),
            "error_message":     self.error_message,
            "error_code":        self.error_code,
            "snapshot_id":       self.snapshot_id,
            "started_at":        self.started_at,
            "completed_at":      self.completed_at,
            "duration_ms":       round(self.duration_ms, 3),
            "metadata":          dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionResult("
            f"execution_id={self.execution_id!r}, "
            f"state={self.final_state.value!r}, "
            f"succeeded={self.succeeded}, "
            f"duration_ms={self.duration_ms:.1f})"
        )

    # ── Factories ─────────────────────────────────────────────────────────────

    @classmethod
    def success(
        cls,
        execution_id: str,
        request_id:   str,
        order_id:     str,
        started_at:   float,
        snapshot_id:  str  = "",
        **kwargs: Any,
    ) -> "ExecutionResult":
        now = time.time()
        return cls(
            execution_id  = execution_id,
            request_id    = request_id,
            order_id      = order_id,
            final_state   = EngineExecutionState.COMPLETED,
            succeeded     = True,
            snapshot_id   = snapshot_id,
            started_at    = started_at,
            completed_at  = now,
            duration_ms   = (now - started_at) * 1_000,
            **kwargs,
        )

    @classmethod
    def failure(
        cls,
        execution_id:     str,
        request_id:       str,
        order_id:         str,
        started_at:       float,
        error_message:    str            = "",
        error_code:       str            = "",
        validation_errors: tuple[str, ...] = (),
        **kwargs: Any,
    ) -> "ExecutionResult":
        now = time.time()
        return cls(
            execution_id      = execution_id,
            request_id        = request_id,
            order_id          = order_id,
            final_state       = EngineExecutionState.FAILED,
            succeeded         = False,
            error_message     = error_message,
            error_code        = error_code,
            validation_errors = validation_errors,
            started_at        = started_at,
            completed_at      = now,
            duration_ms       = (now - started_at) * 1_000,
            **kwargs,
        )

    @classmethod
    def cancelled(
        cls,
        execution_id: str,
        request_id:   str,
        order_id:     str,
        started_at:   float,
        reason:       str = "",
        **kwargs: Any,
    ) -> "ExecutionResult":
        now = time.time()
        return cls(
            execution_id  = execution_id,
            request_id    = request_id,
            order_id      = order_id,
            final_state   = EngineExecutionState.CANCELLED,
            succeeded     = False,
            error_message = reason,
            error_code    = "EX-010",
            started_at    = started_at,
            completed_at  = now,
            duration_ms   = (now - started_at) * 1_000,
            **kwargs,
        )
