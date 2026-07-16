"""iios/execution/positions/engine/position_factory.py
==================================================
EngineFactory — creates Position objects from engine requests using the
M1 PositionFactory, and produces engine-level domain events.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

from iios.execution.positions.lifecycle import (
    Position,
    PositionFactory as LifecycleFactory,
)

from .constants import ACTOR_ENGINE, FACTORY_SYSTEM_ID, VERSION
from .exceptions import PositionCreationError
from .position_events import EngineEvent, make_position_created_event
from .position_request import CreatePositionRequest


class EngineFactory:
    """
    Stateless factory that translates a ``CreatePositionRequest``
    into a fully initialised M1 ``Position`` object.

    Uses ``iios.execution.positions.lifecycle.PositionFactory`` internally.
    """

    def __init__(self) -> None:
        self._inner = LifecycleFactory()

    # ── Construction ──────────────────────────────────────────────────────────

    def create_from_request(self, request: CreatePositionRequest) -> Position:
        """
        Create a new Position from *request*.

        Raises ``PositionCreationError`` if any required field is missing.
        """
        if request.product is None:
            raise PositionCreationError("CreatePositionRequest.product is required")
        if request.direction is None:
            raise PositionCreationError("CreatePositionRequest.direction is required")

        try:
            position = self._inner.create(
                instrument=request.instrument,
                exchange=request.exchange,
                product=request.product,
                direction=request.direction,
                quantity=request.quantity,
                portfolio_id=request.portfolio_id,
                strategy_id=request.strategy_id,
                decision_id=request.decision_id,
                workflow_id=request.workflow_id,
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
            )
        except Exception as exc:
            raise PositionCreationError(
                f"Failed to create position: {exc}",
                context={"instrument": request.instrument, "cause": str(exc)},
            ) from exc

        return position

    # ── Event helper ──────────────────────────────────────────────────────────

    def make_created_event(
        self,
        position: Position,
        actor: str = ACTOR_ENGINE,
    ) -> EngineEvent:
        return make_position_created_event(
            position_id=position.position_id,
            portfolio_id=position.portfolio_id,
            strategy_id=position.strategy_id,
            actor=actor,
        )
