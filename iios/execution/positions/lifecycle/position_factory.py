"""iios/execution/positions/lifecycle/position_factory.py
==================================================
PositionFactory — creates Position instances with validated identifiers
and sensible defaults.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from .constants import (
    ACTOR_FACTORY,
    FACTORY_SYSTEM_ID,
    PositionDirection,
    PositionProduct,
    VERSION,
)
from .exceptions import PositionValidationError
from .position import Position
from .position_event import PositionEvent, make_position_created
from .position_validation import PositionValidator


class PositionFactory:
    """
    Stateless factory for ``Position`` objects.

    Validates all inputs before construction.  Never stores state itself.
    """

    def __init__(self) -> None:
        self._validator = PositionValidator()

    # ── Primary constructor ───────────────────────────────────────────────────

    def create(
        self,
        instrument:   str,
        exchange:     str,
        product:      PositionProduct,
        direction:    PositionDirection,
        quantity:     Decimal,
        *,
        portfolio_id:   str = "",
        strategy_id:    str = "",
        decision_id:    str = "",
        workflow_id:    str = "",
        execution_id:   str = "",
        correlation_id: str = "",
        position_id:    Optional[str] = None,
        max_history:    int = 500,
    ) -> Position:
        """
        Create and return a new ``Position`` in the ``CREATED`` state.

        Parameters
        ----------
        instrument:   Trading symbol (e.g. "NIFTY50", "RELIANCE").
        exchange:     Exchange identifier (e.g. "NSE", "BSE").
        product:      ``PositionProduct`` enum value.
        direction:    ``PositionDirection.LONG`` or ``SHORT``.
        quantity:     Total expected quantity (must be > 0).
        position_id:  Optional override; a UUID4 is generated if omitted.
        """
        if not instrument or not instrument.strip():
            raise PositionValidationError("instrument must be a non-empty string")
        if not exchange or not exchange.strip():
            raise PositionValidationError("exchange must be a non-empty string")
        if quantity <= Decimal(0):
            raise PositionValidationError(f"quantity must be positive; got {quantity}")

        pid = position_id or str(uuid.uuid4())

        position = Position(
            position_id=pid,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            decision_id=decision_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            instrument=instrument,
            exchange=exchange,
            product=product,
            direction=direction,
            quantity=quantity,
            correlation_id=correlation_id,
            max_history=max_history,
        )

        return position

    # ── Convenience wrappers ──────────────────────────────────────────────────

    def create_long(
        self,
        instrument: str,
        exchange:   str,
        product:    PositionProduct,
        quantity:   Decimal,
        **kwargs,
    ) -> Position:
        """Create a LONG position."""
        return self.create(
            instrument=instrument,
            exchange=exchange,
            product=product,
            direction=PositionDirection.LONG,
            quantity=quantity,
            **kwargs,
        )

    def create_short(
        self,
        instrument: str,
        exchange:   str,
        product:    PositionProduct,
        quantity:   Decimal,
        **kwargs,
    ) -> Position:
        """Create a SHORT position."""
        return self.create(
            instrument=instrument,
            exchange=exchange,
            product=product,
            direction=PositionDirection.SHORT,
            quantity=quantity,
            **kwargs,
        )

    # ── Event ─────────────────────────────────────────────────────────────────

    def make_created_event(self, position: Position) -> PositionEvent:
        """Return the POSITION_CREATED domain event for *position*."""
        return make_position_created(
            position_id=position.position_id,
            portfolio_id=position.portfolio_id,
            strategy_id=position.strategy_id,
            actor=ACTOR_FACTORY,
        )
