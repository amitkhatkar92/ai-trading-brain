"""iios/execution/context/execution_request_context.py
==================================================
ExecutionRequestContext — immutable record of all request-level
identifiers and broker context for an execution.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.context.constants import ExecutionMode


@dataclass(frozen=True)
class BrokerContextRef:
    """
    Lightweight, immutable reference to a broker and its
    connection state at the time of the request.

    Does not hold live connections — purely a data record.
    """
    broker_id:        str  = ""
    broker_name:      str  = ""
    is_connected:     bool = False
    execution_mode:   ExecutionMode = ExecutionMode.PAPER
    correlation_id:   str  = ""
    metadata:         dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":      self.broker_id,
            "broker_name":    self.broker_name,
            "is_connected":   self.is_connected,
            "execution_mode": self.execution_mode.value,
            "correlation_id": self.correlation_id,
        }

    def __repr__(self) -> str:
        return (
            f"BrokerContextRef(id={self.broker_id!r}, "
            f"connected={self.is_connected})"
        )


@dataclass(frozen=True)
class ExecutionRequestContext:
    """
    Immutable record of all request-level identifiers for one execution.

    Carries the canonical tracing and correlation identifiers that
    propagate across all C6 modules consuming the ExecutionContext.
    """

    request_context_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Primary identifiers
    request_id:         str = ""
    execution_id:       str = ""
    workflow_id:        str = ""
    order_id:           str = ""
    decision_id:        str = ""
    portfolio_id:       str = ""
    strategy_id:        str = ""

    # Tracing / correlation
    correlation_id:     str = ""
    trace_id:           str = ""
    parent_span_id:     str = ""
    span_id:            str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    # Mode
    execution_mode:     ExecutionMode = ExecutionMode.PAPER

    # Broker context reference
    broker_context:     Optional[BrokerContextRef] = None

    # Timing
    requested_at:       float = field(default_factory=time.time)
    expires_at:         Optional[float] = None

    metadata:           dict[str, Any] = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age_sec(self) -> float:
        return time.time() - self.requested_at

    @property
    def has_broker(self) -> bool:
        return self.broker_context is not None

    @property
    def has_all_ids(self) -> bool:
        return all([
            self.execution_id,
            self.workflow_id,
            self.order_id,
            self.decision_id,
            self.portfolio_id,
            self.strategy_id,
        ])

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_context_id": self.request_context_id,
            "request_id":         self.request_id,
            "execution_id":       self.execution_id,
            "workflow_id":        self.workflow_id,
            "order_id":           self.order_id,
            "decision_id":        self.decision_id,
            "portfolio_id":       self.portfolio_id,
            "strategy_id":        self.strategy_id,
            "correlation_id":     self.correlation_id,
            "trace_id":           self.trace_id,
            "span_id":            self.span_id,
            "execution_mode":     self.execution_mode.value,
            "broker_context":     self.broker_context.to_dict() if self.broker_context else None,
            "requested_at":       self.requested_at,
            "expires_at":         self.expires_at,
            "is_expired":         self.is_expired,
            "has_all_ids":        self.has_all_ids,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionRequestContext("
            f"execution_id={self.execution_id!r}, "
            f"order_id={self.order_id!r}, "
            f"mode={self.execution_mode.value})"
        )
