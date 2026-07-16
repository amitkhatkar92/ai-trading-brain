"""iios/execution/engine/execution_request.py
==================================================
ExecutionRequest — the input contract for the Execution Engine.

An ExecutionRequest carries all information needed by the engine to:
  1. Look up the associated Order.
  2. Validate the execution against portfolio and decision constraints.
  3. Select execution mode.
  4. Build the ExecutionContext.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .constants import ExecutionMode, ExecutionPriority


@dataclass
class ExecutionRequest:
    """
    Input submitted to the Execution Engine.

    Fields
    ------
    request_id    : Unique identifier (auto-generated if not supplied).
    execution_id  : Caller-assigned execution session ID.  If empty the
                    engine will generate one.
    order_id      : ID of the Order (from M1 OrderRegistry) to execute.
    decision_id   : ID of the originating Decision.
    portfolio_id  : Portfolio this execution belongs to.
    strategy_id   : Strategy that generated this request.
    execution_mode: PAPER / SIMULATION / LIVE.
    priority      : Scheduling priority.
    requested_by  : Actor that submitted the request (user, strategy, risk …).
    requested_at  : Unix timestamp when the request was created.
    expires_at    : Optional hard deadline; engine will cancel if exceeded.
    tags          : Optional labels for observability.
    metadata      : Arbitrary key/value payload.
    """

    # ── Identifiers ────────────────────────────────────────────────────────────
    request_id:   str = field(default_factory=lambda: f"REQ-{uuid.uuid4().hex[:16].upper()}")
    execution_id: str = ""          # engine fills this when empty
    order_id:     str = ""
    decision_id:  str = ""
    portfolio_id: str = ""
    strategy_id:  str = ""

    # ── Execution parameters ───────────────────────────────────────────────────
    execution_mode: ExecutionMode     = ExecutionMode.PAPER
    priority:       ExecutionPriority = ExecutionPriority.NORMAL

    # ── Provenance ────────────────────────────────────────────────────────────
    requested_by: str            = ""
    requested_at: float          = field(default_factory=time.time)
    expires_at:   Optional[float] = None

    # ── Observability ─────────────────────────────────────────────────────────
    tags:     frozenset[str]  = field(default_factory=frozenset)
    notes:    str             = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Derived helpers ────────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        """True if the request has passed its expiry deadline."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age_sec(self) -> float:
        """Seconds since the request was created."""
        return time.time() - self.requested_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "execution_id":   self.execution_id,
            "order_id":       self.order_id,
            "decision_id":    self.decision_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "execution_mode": self.execution_mode.value,
            "priority":       self.priority.value,
            "requested_by":   self.requested_by,
            "requested_at":   self.requested_at,
            "expires_at":     self.expires_at,
            "tags":           sorted(self.tags),
            "notes":          self.notes,
            "metadata":       dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionRequest("
            f"request_id={self.request_id!r}, "
            f"order_id={self.order_id!r}, "
            f"mode={self.execution_mode.value!r}, "
            f"priority={self.priority.value!r})"
        )
