"""iios/execution/positions/snapshot/position_snapshot.py
==================================================
PositionSnapshot — the canonical published representation of a
trading position.

PositionSnapshot is:
  * Immutable (frozen dataclass)
  * The ONLY object published outside the Position Management subsystem
  * Versioned (snapshot_version per position, VERSION for schema)
  * Fully serialisable via to_dict() / from_dict()
  * Self-describing via audit_metadata

Downstream consumers (Integration, Risk, Recovery, Analytics,
Compliance, Reporting) MUST consume PositionSnapshot.
They must NOT access internal Position objects directly.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .constants import PUBLISHABLE_STATUSES, TERMINAL_STATUSES, VERSION, SnapshotStatus


@dataclass(frozen=True)
class PositionSnapshot:
    """
    Immutable, point-in-time published view of a single trading position.

    All ``Decimal`` fields are stored as ``str`` to preserve precision
    across serialisation boundaries.

    Responsibilities
    ----------------
    * Carry all validated position data as an immutable value object.
    * Provide convenience properties for common checks.
    * Serialise to / deserialise from plain dictionaries.
    * Track snapshot provenance through ``audit_metadata``.

    Non-responsibilities
    --------------------
    * No calculations (all values are pre-computed by the builder).
    * No state-machine logic.
    * No broker connectivity.
    * No validation (SnapshotValidator does that).
    """

    # ── Snapshot header ───────────────────────────────────────────────────────
    snapshot_id:      str
    snapshot_version: int          # version counter per position (1, 2, 3 …)
    snapshot_status:  str          # SnapshotStatus.value

    # ── Identity ──────────────────────────────────────────────────────────────
    position_id:  str
    execution_id: str
    order_id:     str
    portfolio_id: str
    strategy_id:  str
    decision_id:  str
    workflow_id:  str
    correlation_id: str

    # ── Instrument ────────────────────────────────────────────────────────────
    instrument: str
    exchange:   str
    product:    str              # PositionProduct.value
    direction:  str              # PositionDirection.value

    # ── Position state ────────────────────────────────────────────────────────
    lifecycle_state: str         # PositionState.value
    risk_state:      str         # RiskLevel.value or "" if not tracked

    # ── Quantities (Decimal stored as str) ────────────────────────────────────
    current_quantity: str        # open_quantity
    closed_quantity:  str

    # ── Prices ────────────────────────────────────────────────────────────────
    average_entry_price: str
    average_exit_price:  str
    current_price:       str     # externally provided market price or "0"
    market_value:        str     # current_price * current_quantity

    # ── PnL ───────────────────────────────────────────────────────────────────
    realized_pnl:   str
    unrealized_pnl: str

    # ── Risk metrics ──────────────────────────────────────────────────────────
    exposure:         str        # from PositionRiskState.current_exposure
    margin_used:      str
    margin_available: str

    # ── Duration ──────────────────────────────────────────────────────────────
    execution_duration_s: float  # time.time() − position.created_at at build time

    # ── Embedded metadata (dict for serialisation compatibility) ──────────────
    position_statistics: Dict[str, Any] = field(default_factory=dict, compare=False)
    position_metadata:   Dict[str, Any] = field(default_factory=dict, compare=False)
    audit_metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    position_created_at: float = 0.0
    position_updated_at: float = 0.0
    snapshot_taken_at:   float = 0.0
    published_at:        float = 0.0   # 0.0 = not yet published
    archived_at:         float = 0.0   # 0.0 = not yet archived

    # ── Schema version ────────────────────────────────────────────────────────
    version: str = VERSION

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def is_draft(self) -> bool:
        return self.snapshot_status == SnapshotStatus.DRAFT.value

    @property
    def is_valid(self) -> bool:
        return self.snapshot_status == SnapshotStatus.VALID.value

    @property
    def is_published(self) -> bool:
        return self.snapshot_status == SnapshotStatus.PUBLISHED.value

    @property
    def is_archived(self) -> bool:
        return self.snapshot_status == SnapshotStatus.ARCHIVED.value

    @property
    def is_invalid(self) -> bool:
        return self.snapshot_status == SnapshotStatus.INVALID.value

    @property
    def is_publishable(self) -> bool:
        return SnapshotStatus(self.snapshot_status) in PUBLISHABLE_STATUSES

    @property
    def is_terminal(self) -> bool:
        return SnapshotStatus(self.snapshot_status) in TERMINAL_STATUSES

    @property
    def age_s(self) -> float:
        """Seconds elapsed since this snapshot was taken."""
        return time.time() - self.snapshot_taken_at

    # ── Status transitions (produce new frozen instance) ─────────────────────

    def as_valid(self) -> "PositionSnapshot":
        return dataclasses.replace(self, snapshot_status=SnapshotStatus.VALID.value)

    def as_published(self) -> "PositionSnapshot":
        return dataclasses.replace(
            self,
            snapshot_status=SnapshotStatus.PUBLISHED.value,
            published_at=time.time(),
        )

    def as_archived(self) -> "PositionSnapshot":
        return dataclasses.replace(
            self,
            snapshot_status=SnapshotStatus.ARCHIVED.value,
            archived_at=time.time(),
        )

    def as_invalid(self) -> "PositionSnapshot":
        return dataclasses.replace(self, snapshot_status=SnapshotStatus.INVALID.value)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            # header
            "snapshot_id":          self.snapshot_id,
            "snapshot_version":     self.snapshot_version,
            "snapshot_status":      self.snapshot_status,
            # identity
            "position_id":          self.position_id,
            "execution_id":         self.execution_id,
            "order_id":             self.order_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "decision_id":          self.decision_id,
            "workflow_id":          self.workflow_id,
            "correlation_id":       self.correlation_id,
            # instrument
            "instrument":           self.instrument,
            "exchange":             self.exchange,
            "product":              self.product,
            "direction":            self.direction,
            # state
            "lifecycle_state":      self.lifecycle_state,
            "risk_state":           self.risk_state,
            # quantities
            "current_quantity":     self.current_quantity,
            "closed_quantity":      self.closed_quantity,
            # prices
            "average_entry_price":  self.average_entry_price,
            "average_exit_price":   self.average_exit_price,
            "current_price":        self.current_price,
            "market_value":         self.market_value,
            # pnl
            "realized_pnl":         self.realized_pnl,
            "unrealized_pnl":       self.unrealized_pnl,
            # risk
            "exposure":             self.exposure,
            "margin_used":          self.margin_used,
            "margin_available":     self.margin_available,
            # duration
            "execution_duration_s": self.execution_duration_s,
            # metadata
            "position_statistics":  dict(self.position_statistics),
            "position_metadata":    dict(self.position_metadata),
            "audit_metadata":       dict(self.audit_metadata),
            # timestamps
            "position_created_at":  self.position_created_at,
            "position_updated_at":  self.position_updated_at,
            "snapshot_taken_at":    self.snapshot_taken_at,
            "published_at":         self.published_at,
            "archived_at":          self.archived_at,
            # schema
            "version":              self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositionSnapshot":
        return cls(
            snapshot_id=data["snapshot_id"],
            snapshot_version=int(data.get("snapshot_version", 1)),
            snapshot_status=data.get("snapshot_status", SnapshotStatus.DRAFT.value),
            position_id=data["position_id"],
            execution_id=data.get("execution_id", ""),
            order_id=data.get("order_id", ""),
            portfolio_id=data.get("portfolio_id", ""),
            strategy_id=data.get("strategy_id", ""),
            decision_id=data.get("decision_id", ""),
            workflow_id=data.get("workflow_id", ""),
            correlation_id=data.get("correlation_id", ""),
            instrument=data["instrument"],
            exchange=data.get("exchange", ""),
            product=data.get("product", ""),
            direction=data.get("direction", ""),
            lifecycle_state=data.get("lifecycle_state", ""),
            risk_state=data.get("risk_state", ""),
            current_quantity=data.get("current_quantity", "0"),
            closed_quantity=data.get("closed_quantity", "0"),
            average_entry_price=data.get("average_entry_price", "0"),
            average_exit_price=data.get("average_exit_price", "0"),
            current_price=data.get("current_price", "0"),
            market_value=data.get("market_value", "0"),
            realized_pnl=data.get("realized_pnl", "0"),
            unrealized_pnl=data.get("unrealized_pnl", "0"),
            exposure=data.get("exposure", "0"),
            margin_used=data.get("margin_used", "0"),
            margin_available=data.get("margin_available", "0"),
            execution_duration_s=float(data.get("execution_duration_s", 0.0)),
            position_statistics=dict(data.get("position_statistics", {})),
            position_metadata=dict(data.get("position_metadata", {})),
            audit_metadata=dict(data.get("audit_metadata", {})),
            position_created_at=float(data.get("position_created_at", 0.0)),
            position_updated_at=float(data.get("position_updated_at", 0.0)),
            snapshot_taken_at=float(data.get("snapshot_taken_at", 0.0)),
            published_at=float(data.get("published_at", 0.0)),
            archived_at=float(data.get("archived_at", 0.0)),
            version=data.get("version", VERSION),
        )

    def __repr__(self) -> str:
        return (
            f"PositionSnapshot(snapshot_id={self.snapshot_id[:8]}…, "
            f"position_id={self.position_id!r}, "
            f"instrument={self.instrument!r}, "
            f"status={self.snapshot_status!r}, "
            f"version={self.snapshot_version})"
        )
