"""iios/execution/positions/integration/position_integration_request.py
==================================================
Integration-layer request types for all position operations.

These are the ONLY request types accepted by the public API of
PositionIntegrationEngine.  They wrap the underlying engine
request types and add integration-specific metadata.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional, TYPE_CHECKING

from iios.execution.positions.lifecycle import PositionDirection, PositionProduct, PositionState
from iios.execution.positions.engine import (
    CreatePositionRequest,
    UpdatePositionRequest,
    ClosePositionRequest,
    SyncPositionRequest,
    ArchivePositionRequest,
    QueryPositionRequest,
    ExecutionSnapshot,
)

from .constants import IntegrationOperationType, ACTOR_INTEGRATION
from .position_integration_context import IntegrationContext

if TYPE_CHECKING:
    from iios.execution.positions.risk import RiskLimits


# ── Base ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BaseIntegrationRequest:
    """Common fields for every integration request."""

    request_id:     str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""
    actor:          str = ACTOR_INTEGRATION
    created_at:     float = field(default_factory=time.time)
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def operation_type(self) -> IntegrationOperationType:
        raise NotImplementedError


# ── Create ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CreatePositionIntegrationRequest(BaseIntegrationRequest):
    """
    Request to create a new managed position.

    Wraps :class:`CreatePositionRequest` and adds:
    * ``risk_limits`` — optional custom risk limits (defaults used if absent)
    * ``auto_publish_snapshot`` — whether to publish the initial snapshot
    """

    instrument:              str                       = ""
    exchange:                str                       = ""
    product:                 Optional[PositionProduct]  = None
    direction:               Optional[PositionDirection] = None
    quantity:                Decimal                   = Decimal(0)
    portfolio_id:            str                       = ""
    strategy_id:             str                       = ""
    decision_id:             str                       = ""
    workflow_id:             str                       = ""
    execution_id:            str                       = ""
    risk_limits:             Optional[Any]             = None   # RiskLimits
    auto_publish_snapshot:   bool                      = True

    @property
    def operation_type(self) -> IntegrationOperationType:
        return IntegrationOperationType.CREATE

    def to_engine_request(self) -> CreatePositionRequest:
        return CreatePositionRequest(
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            actor=self.actor,
            instrument=self.instrument,
            exchange=self.exchange,
            product=self.product,
            direction=self.direction,
            quantity=self.quantity,
            portfolio_id=self.portfolio_id,
            strategy_id=self.strategy_id,
            decision_id=self.decision_id,
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
        )


# ── Update ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class UpdatePositionIntegrationRequest(BaseIntegrationRequest):
    """
    Request to update an existing position.

    Wraps :class:`UpdatePositionRequest`.
    """

    position_id:     str                    = ""
    open_quantity:   Optional[Decimal]      = None
    closed_quantity: Optional[Decimal]      = None
    avg_entry_price: Optional[Decimal]      = None
    avg_exit_price:  Optional[Decimal]      = None
    realized_pnl:    Optional[Decimal]      = None
    unrealized_pnl:  Optional[Decimal]      = None
    new_state:       Optional[PositionState] = None
    reason:          str                    = ""
    auto_publish_snapshot: bool             = False

    @property
    def operation_type(self) -> IntegrationOperationType:
        return IntegrationOperationType.UPDATE

    def to_engine_request(self) -> UpdatePositionRequest:
        return UpdatePositionRequest(
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            actor=self.actor,
            position_id=self.position_id,
            open_quantity=self.open_quantity,
            closed_quantity=self.closed_quantity,
            avg_entry_price=self.avg_entry_price,
            avg_exit_price=self.avg_exit_price,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            new_state=self.new_state,
            reason=self.reason,
        )


# ── Close ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClosePositionIntegrationRequest(BaseIntegrationRequest):
    """
    Request to close a position.

    Wraps :class:`ClosePositionRequest`.
    """

    position_id:             str              = ""
    avg_exit_price:          Optional[Decimal] = None
    realized_pnl:            Optional[Decimal] = None
    reason:                  str              = ""
    auto_publish_snapshot:   bool             = True

    @property
    def operation_type(self) -> IntegrationOperationType:
        return IntegrationOperationType.CLOSE

    def to_engine_request(self) -> ClosePositionRequest:
        return ClosePositionRequest(
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            actor=self.actor,
            position_id=self.position_id,
            avg_exit_price=self.avg_exit_price,
            realized_pnl=self.realized_pnl,
            reason=self.reason,
        )


# ── Sync ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SyncPositionIntegrationRequest(BaseIntegrationRequest):
    """
    Request to synchronize execution data into a position.

    Wraps :class:`SyncPositionRequest`.
    """

    position_id:        str                          = ""
    execution_snapshot: Optional[ExecutionSnapshot]  = None
    auto_publish_snapshot: bool                      = False

    @property
    def operation_type(self) -> IntegrationOperationType:
        return IntegrationOperationType.SYNC

    def to_engine_request(self) -> SyncPositionRequest:
        return SyncPositionRequest(
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            actor=self.actor,
            position_id=self.position_id,
            execution_snapshot=self.execution_snapshot,
        )


# ── Archive ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ArchivePositionIntegrationRequest(BaseIntegrationRequest):
    """
    Request to archive a CLOSED position.

    Wraps :class:`ArchivePositionRequest`.
    """

    position_id: str = ""
    reason:      str = ""
    auto_publish_snapshot: bool = True

    @property
    def operation_type(self) -> IntegrationOperationType:
        return IntegrationOperationType.ARCHIVE

    def to_engine_request(self) -> ArchivePositionRequest:
        return ArchivePositionRequest(
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            actor=self.actor,
            position_id=self.position_id,
            reason=self.reason,
        )


# ── Query ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class QueryPositionIntegrationRequest(BaseIntegrationRequest):
    """
    Request to query positions.

    Supports lookup by position_id, portfolio, strategy, instrument,
    or all-active.
    """

    position_id:       str  = ""
    portfolio_id:      str  = ""
    strategy_id:       str  = ""
    workflow_id:       str  = ""
    instrument:        str  = ""
    include_active:    bool = True
    include_closed:    bool = False
    include_archived:  bool = False
    limit:             int  = 100

    @property
    def operation_type(self) -> IntegrationOperationType:
        return IntegrationOperationType.QUERY


# ── Publish Snapshot ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PublishSnapshotIntegrationRequest(BaseIntegrationRequest):
    """Request to explicitly publish a snapshot for a given position."""

    position_id: str = ""

    @property
    def operation_type(self) -> IntegrationOperationType:
        return IntegrationOperationType.PUBLISH_SNAPSHOT
