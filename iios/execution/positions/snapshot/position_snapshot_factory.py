"""iios/execution/positions/snapshot/position_snapshot_factory.py
==================================================
PositionSnapshotFactory — convenience wrappers around
PositionSnapshotBuilder for common snapshot creation patterns.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from iios.execution.positions.lifecycle import Position

from .constants import ACTOR_BUILDER
from .position_snapshot import PositionSnapshot
from .position_snapshot_builder import PositionSnapshotBuilder

if TYPE_CHECKING:
    from iios.execution.positions.risk.position_risk_state import PositionRiskState


class PositionSnapshotFactory:
    """
    Convenience factory wrapping ``PositionSnapshotBuilder``.

    All methods delegate to an internal builder instance.

    Non-responsibilities
    --------------------
    * No validation (SnapshotValidator owns that).
    * No persistence (PositionSnapshotStore owns that).
    """

    def __init__(self) -> None:
        self._builder = PositionSnapshotBuilder()

    def create(
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
        Create a ``PositionSnapshot`` from *position* and optional risk/price data.

        This is the primary factory method. All other methods in this class
        delegate here.

        Returns a snapshot in ``DRAFT`` status.
        """
        return self._builder.build(
            position,
            risk_state=risk_state,
            current_price=current_price,
            order_id=order_id,
            snapshot_version=snapshot_version,
            built_by=built_by,
        )

    def create_minimal(
        self,
        position:         Position,
        snapshot_version: int = 1,
    ) -> PositionSnapshot:
        """
        Create a minimal snapshot with no risk state or market price.

        Useful for quick identity-only snapshots.
        """
        return self._builder.build(
            position,
            snapshot_version=snapshot_version,
        )

    def create_with_risk(
        self,
        position:         Position,
        risk_state:       "PositionRiskState",
        snapshot_version: int = 1,
    ) -> PositionSnapshot:
        """Create a snapshot with full risk state embedded."""
        return self._builder.build(
            position,
            risk_state=risk_state,
            snapshot_version=snapshot_version,
        )

    def create_with_price(
        self,
        position:         Position,
        current_price:    Decimal,
        snapshot_version: int = 1,
    ) -> PositionSnapshot:
        """Create a snapshot with a current market price for market_value computation."""
        return self._builder.build(
            position,
            current_price=current_price,
            snapshot_version=snapshot_version,
        )
