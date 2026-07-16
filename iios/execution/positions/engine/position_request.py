"""iios/execution/positions/engine/position_request.py
==================================================
Request types for all six Position Engine operations.

Also defines ``ExecutionSnapshot`` — the data contract for
synchronizing execution-layer state into the engine.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from iios.execution.positions.lifecycle import (
    PositionDirection,
    PositionProduct,
    PositionState,
)

from .constants import OperationType


# ── ExecutionSnapshot ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExecutionSnapshot:
    """
    Point-in-time execution data from the execution layer.

    Passed into ``SyncPositionRequest`` to update a position with
    the latest execution-confirmed quantities, prices, and PnL.
    """

    execution_id:    str
    position_id:     str
    instrument:      str
    exchange:        str
    open_quantity:   Decimal
    closed_quantity: Decimal
    avg_entry_price: Decimal
    avg_exit_price:  Decimal
    realized_pnl:    Decimal
    unrealized_pnl:  Decimal
    snapped_at:      float = field(default_factory=time.time)
    metadata:        Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def total_quantity(self) -> Decimal:
        return self.open_quantity + self.closed_quantity

    @property
    def is_fully_closed(self) -> bool:
        return self.open_quantity == Decimal(0) and self.closed_quantity > Decimal(0)

    def to_dict(self) -> dict:
        return {
            "execution_id":    self.execution_id,
            "position_id":     self.position_id,
            "instrument":      self.instrument,
            "exchange":        self.exchange,
            "open_quantity":   str(self.open_quantity),
            "closed_quantity": str(self.closed_quantity),
            "avg_entry_price": str(self.avg_entry_price),
            "avg_exit_price":  str(self.avg_exit_price),
            "realized_pnl":    str(self.realized_pnl),
            "unrealized_pnl":  str(self.unrealized_pnl),
            "snapped_at":      self.snapped_at,
        }


# ── Base request ──────────────────────────────────────────────────────────────

@dataclass
class PositionRequest:
    """Common fields shared by all engine requests."""
    request_id:     str  = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str  = ""
    actor:          str  = ""
    created_at:     float = field(default_factory=time.time)
    metadata:       Dict[str, Any] = field(default_factory=dict)

    @property
    def operation_type(self) -> OperationType:
        raise NotImplementedError


# ── CreatePositionRequest ─────────────────────────────────────────────────────

@dataclass
class CreatePositionRequest(PositionRequest):
    """Request to create a new position via the engine."""

    instrument:     str                  = ""
    exchange:       str                  = ""
    product:        Optional[PositionProduct]   = None
    direction:      Optional[PositionDirection] = None
    quantity:       Decimal              = Decimal(0)
    portfolio_id:   str                  = ""
    strategy_id:    str                  = ""
    decision_id:    str                  = ""
    workflow_id:    str                  = ""
    execution_id:   str                  = ""
    # If True, the engine immediately transitions the position to OPENING
    auto_open:      bool                 = True

    @property
    def operation_type(self) -> OperationType:
        return OperationType.CREATE_POSITION


# ── UpdatePositionRequest ─────────────────────────────────────────────────────

@dataclass
class UpdatePositionRequest(PositionRequest):
    """Request to update fields and/or lifecycle state of an existing position."""

    position_id:     str                       = ""
    open_quantity:   Optional[Decimal]         = None
    closed_quantity: Optional[Decimal]         = None
    avg_entry_price: Optional[Decimal]         = None
    avg_exit_price:  Optional[Decimal]         = None
    realized_pnl:    Optional[Decimal]         = None
    unrealized_pnl:  Optional[Decimal]         = None
    new_state:       Optional[PositionState]   = None
    reason:          str                       = ""

    @property
    def operation_type(self) -> OperationType:
        return OperationType.UPDATE_POSITION

    @property
    def has_field_updates(self) -> bool:
        return any(v is not None for v in (
            self.open_quantity, self.closed_quantity,
            self.avg_entry_price, self.avg_exit_price,
            self.realized_pnl, self.unrealized_pnl,
        ))


# ── ClosePositionRequest ──────────────────────────────────────────────────────

@dataclass
class ClosePositionRequest(PositionRequest):
    """
    Request to close a position.

    Drives the lifecycle through CLOSING → CLOSED.
    avg_exit_price and realized_pnl are applied before the state change.
    """

    position_id:    str              = ""
    avg_exit_price: Optional[Decimal] = None
    realized_pnl:   Optional[Decimal] = None
    reason:         str              = ""

    @property
    def operation_type(self) -> OperationType:
        return OperationType.CLOSE_POSITION


# ── SyncPositionRequest ───────────────────────────────────────────────────────

@dataclass
class SyncPositionRequest(PositionRequest):
    """
    Request to synchronize execution data into a position.

    Supply either an ``ExecutionSnapshot`` (preferred) or individual
    field overrides.  If both are present, individual overrides take
    precedence over snapshot values.

    If ``new_state`` is specified the engine applies the lifecycle
    transition after the field updates.
    """

    position_id:      str                        = ""
    execution_snapshot: Optional[ExecutionSnapshot] = None
    open_quantity:    Optional[Decimal]          = None
    closed_quantity:  Optional[Decimal]          = None
    avg_entry_price:  Optional[Decimal]          = None
    avg_exit_price:   Optional[Decimal]          = None
    realized_pnl:     Optional[Decimal]          = None
    unrealized_pnl:   Optional[Decimal]          = None
    new_state:        Optional[PositionState]    = None
    reason:           str                        = ""

    @property
    def operation_type(self) -> OperationType:
        return OperationType.SYNC_POSITION


# ── ArchivePositionRequest ────────────────────────────────────────────────────

@dataclass
class ArchivePositionRequest(PositionRequest):
    """
    Request to archive a CLOSED position.

    The position must be in the CLOSED lifecycle state; the engine
    transitions it to ARCHIVED.
    """

    position_id: str = ""
    reason:      str = ""

    @property
    def operation_type(self) -> OperationType:
        return OperationType.ARCHIVE_POSITION


# ── QueryPositionRequest ──────────────────────────────────────────────────────

@dataclass
class QueryPositionRequest(PositionRequest):
    """
    Request to query one or more positions.

    Supply ``position_id`` to fetch a single position.
    Supply filters (portfolio_id, strategy_id, state, instrument)
    to fetch a filtered list.  All filters are optional and AND-ed.
    """

    position_id:  Optional[str]           = None
    portfolio_id: Optional[str]           = None
    strategy_id:  Optional[str]           = None
    instrument:   Optional[str]           = None
    state:        Optional[PositionState] = None
    limit:        int                     = 1_000

    @property
    def operation_type(self) -> OperationType:
        return OperationType.QUERY_POSITION

    @property
    def is_single_lookup(self) -> bool:
        return self.position_id is not None
