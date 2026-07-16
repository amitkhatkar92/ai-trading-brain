"""iios/execution/engine/execution_snapshot.py
==================================================
ExecutionSnapshot — a point-in-time capture of an execution's state.

Published after the PREPARING phase completes and again when the
execution reaches a terminal state.  Downstream components (risk,
monitoring, broker adapters) consume snapshots.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .execution_state import EngineExecutionState


@dataclass(frozen=True)
class ExecutionSnapshot:
    """
    Immutable point-in-time capture of one execution's state.

    Published by the engine after PREPARING and at terminal states.

    Attributes
    ----------
    snapshot_id        : Unique snapshot identifier.
    execution_id       : Parent execution session.
    request_id         : Originating request.
    order_id           : Associated order.
    portfolio_id       : Portfolio this execution belongs to.
    strategy_id        : Originating strategy.
    execution_state    : Current engine execution state.
    execution_mode     : PAPER / SIMULATION / LIVE.
    is_terminal        : True when state is COMPLETED / FAILED / CANCELLED.
    context_completeness : Fraction of optional context fields present [0–1].
    captured_at        : Unix timestamp.
    metadata           : Arbitrary payload.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    snapshot_id:  str = field(default_factory=lambda: f"SNAP-{uuid.uuid4().hex[:16].upper()}")
    execution_id: str = ""
    request_id:   str = ""
    order_id:     str = ""
    portfolio_id: str = ""
    strategy_id:  str = ""

    # ── State ─────────────────────────────────────────────────────────────────
    execution_state:      EngineExecutionState = EngineExecutionState.IDLE
    execution_mode:       str                  = "PAPER"
    is_terminal:          bool                 = False

    # ── Context quality ───────────────────────────────────────────────────────
    context_completeness: float = 0.0
    has_order:            bool  = False
    has_portfolio:        bool  = False
    has_decision:         bool  = False
    has_strategy:         bool  = False

    # ── Timing ────────────────────────────────────────────────────────────────
    captured_at:      float = field(default_factory=time.time)
    started_at:       float = 0.0
    duration_ms_so_far: float = 0.0

    # ── Outcome (set on terminal snapshots) ───────────────────────────────────
    succeeded:     Optional[bool] = None
    error_message: str            = ""

    # ── Extra ─────────────────────────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":           self.snapshot_id,
            "execution_id":          self.execution_id,
            "request_id":            self.request_id,
            "order_id":              self.order_id,
            "portfolio_id":          self.portfolio_id,
            "strategy_id":           self.strategy_id,
            "execution_state":       self.execution_state.value,
            "execution_mode":        self.execution_mode,
            "is_terminal":           self.is_terminal,
            "context_completeness":  round(self.context_completeness, 4),
            "has_order":             self.has_order,
            "has_portfolio":         self.has_portfolio,
            "has_decision":          self.has_decision,
            "has_strategy":          self.has_strategy,
            "captured_at":           self.captured_at,
            "started_at":            self.started_at,
            "duration_ms_so_far":    round(self.duration_ms_so_far, 3),
            "succeeded":             self.succeeded,
            "error_message":         self.error_message,
            "metadata":              dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionSnapshot("
            f"execution_id={self.execution_id!r}, "
            f"state={self.execution_state.value!r}, "
            f"is_terminal={self.is_terminal})"
        )
