"""iios/execution/positions/snapshot/position_snapshot_builder.py
==================================================
PositionSnapshotBuilder — builds PositionSnapshot objects from
validated source data.

Accepts:
  * A live ``Position`` (required)
  * A ``PositionRiskState`` (optional — risk fields default to "0"/empty)
  * Current market price (optional — market_value defaults to "0")
  * An explicit order_id (optional)
  * Snapshot version (managed by the store; default 1)

Rejects:
  * Missing required position identifiers
  * Position with empty instrument or empty position_id
  * Any source that fails pre-build validation

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, TYPE_CHECKING

from iios.execution.positions.lifecycle import Position

from .constants import ACTOR_BUILDER, VERSION, SnapshotStatus
from .exceptions import SnapshotBuildError
from .position_snapshot import PositionSnapshot
from .position_snapshot_metadata import make_audit_metadata

if TYPE_CHECKING:
    from iios.execution.positions.risk.position_risk_state import PositionRiskState


_ZERO = Decimal("0")


class PositionSnapshotBuilder:
    """
    Builds immutable ``PositionSnapshot`` objects from validated source data.

    Non-responsibilities
    --------------------
    * No persistence.
    * No state-machine logic.
    * No risk evaluation.
    * No validation of the finished snapshot (SnapshotValidator does that).
    """

    def build(
        self,
        position:         Position,
        *,
        risk_state:       Optional["PositionRiskState"] = None,
        current_price:    Optional[Decimal]             = None,
        order_id:         str                           = "",
        snapshot_version: int                           = 1,
        built_by:         str                           = ACTOR_BUILDER,
    ) -> PositionSnapshot:
        """
        Build and return a ``PositionSnapshot`` in ``DRAFT`` status.

        Parameters
        ----------
        position
            Live ``Position`` object; must have non-empty position_id and instrument.
        risk_state
            Optional ``PositionRiskState``; if absent, risk fields default to "0" / "".
        current_price
            Current market price for market_value computation.
        order_id
            Optional external order identifier to embed in the snapshot.
        snapshot_version
            Version counter for this position (1 = first snapshot).
        built_by
            Actor ID recorded in the audit trail.

        Raises
        ------
        SnapshotBuildError
            If the position fails minimum identity requirements.
        """
        t0 = time.perf_counter()
        self._validate_position(position)

        now  = time.time()
        sid  = str(uuid.uuid4())

        # ── Quantities ────────────────────────────────────────────────────────
        open_qty   = position.open_quantity
        closed_qty = position.closed_quantity

        # ── Prices ────────────────────────────────────────────────────────────
        mkt_price = current_price if current_price is not None else _ZERO
        mkt_value = mkt_price * open_qty

        # ── Risk fields ───────────────────────────────────────────────────────
        if risk_state is not None:
            risk_level_str   = risk_state.risk_level.value
            exposure_str     = str(risk_state.current_exposure)
            margin_used_str  = str(risk_state.margin_used)
            margin_avail_str = str(risk_state.margin_available)
        else:
            risk_level_str   = ""
            exposure_str     = "0"
            margin_used_str  = "0"
            margin_avail_str = "0"

        # ── Position statistics ───────────────────────────────────────────────
        position_statistics = self._build_position_statistics(position, now)

        # ── Position metadata ─────────────────────────────────────────────────
        try:
            position_metadata = position.metadata.to_dict()
        except AttributeError:
            position_metadata = {}

        # ── Audit metadata ────────────────────────────────────────────────────
        build_duration_ms = (time.perf_counter() - t0) * 1_000
        audit = make_audit_metadata(
            source_position_id=position.position_id,
            source_snapshot_version=snapshot_version,
            build_duration_ms=build_duration_ms,
            validation_passed=False,  # will be updated after validation
            built_by=built_by,
        )

        return PositionSnapshot(
            # header
            snapshot_id=sid,
            snapshot_version=snapshot_version,
            snapshot_status=SnapshotStatus.DRAFT.value,
            # identity
            position_id=position.position_id,
            execution_id=position.execution_id,
            order_id=order_id,
            portfolio_id=position.portfolio_id,
            strategy_id=position.strategy_id,
            decision_id=position.decision_id,
            workflow_id=position.workflow_id,
            correlation_id=getattr(position, "correlation_id", ""),
            # instrument
            instrument=position.instrument,
            exchange=position.exchange,
            product=position.product.value,
            direction=position.direction.value,
            # state
            lifecycle_state=position.state.value,
            risk_state=risk_level_str,
            # quantities
            current_quantity=str(open_qty),
            closed_quantity=str(closed_qty),
            # prices
            average_entry_price=str(position.average_entry_price),
            average_exit_price=str(position.average_exit_price),
            current_price=str(mkt_price),
            market_value=str(mkt_value),
            # pnl
            realized_pnl=str(position.realized_pnl),
            unrealized_pnl=str(position.unrealized_pnl),
            # risk
            exposure=exposure_str,
            margin_used=margin_used_str,
            margin_available=margin_avail_str,
            # duration
            execution_duration_s=now - position.created_at,
            # metadata
            position_statistics=position_statistics,
            position_metadata=position_metadata,
            audit_metadata=audit.to_dict(),
            # timestamps
            position_created_at=position.created_at,
            position_updated_at=position.updated_at,
            snapshot_taken_at=now,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _validate_position(self, position: Position) -> None:
        errors = []
        if not position.position_id:
            errors.append("position_id must not be empty")
        if not position.instrument:
            errors.append("instrument must not be empty")
        if not position.exchange:
            errors.append("exchange must not be empty")
        if position.product is None:
            errors.append("product must not be None")
        if position.direction is None:
            errors.append("direction must not be None")
        if errors:
            raise SnapshotBuildError(
                "Position failed pre-build validation",
                position.position_id if position.position_id else "",
                errors=tuple(errors),
            )

    def _build_position_statistics(
        self,
        position: Position,
        now: float,
    ) -> Dict[str, Any]:
        holding_s = now - position.created_at
        try:
            fill_ratio = float(position.fill_ratio)
        except Exception:
            fill_ratio = 0.0
        return {
            "holding_time_s":  holding_s,
            "fill_ratio":      fill_ratio,
            "total_pnl":       str(position.total_pnl),
            "is_active":       position.is_active,
            "is_closed":       position.is_closed,
        }
