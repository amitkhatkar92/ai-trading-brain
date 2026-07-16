"""iios/execution/positions/risk/position_risk_factory.py
==================================================
RiskFactory — creates PositionRiskState objects from Position instances.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

from iios.execution.positions.lifecycle import Position

from .constants import ACTOR_RISK, FACTORY_SYSTEM_ID
from .exceptions import PositionRiskValidationError
from .position_risk_limits import RiskLimits
from .position_risk_state import PositionRiskState
from .position_risk_threshold import RiskThreshold


class RiskFactory:
    """
    Creates ``PositionRiskState`` objects from live ``Position`` instances.

    Non-responsibilities
    --------------------
    * No state machine enforcement.
    * No registry interaction.
    * No limit enforcement.
    """

    def create(
        self,
        position:   Position,
        limits:     RiskLimits,
        thresholds: RiskThreshold,
    ) -> PositionRiskState:
        """
        Create a ``PositionRiskState`` for *position*.

        Raises
        ------
        PositionRiskValidationError
            If the position fails minimum identity requirements.
        """
        self._validate(position)
        return PositionRiskState(
            position_id=position.position_id,
            portfolio_id=getattr(position, "portfolio_id", ""),
            strategy_id=getattr(position, "strategy_id", ""),
            instrument=position.instrument,
        )

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self, position: Position) -> None:
        errors = []
        if not position.position_id:
            errors.append("position_id must not be empty")
        if not position.instrument:
            errors.append("instrument must not be empty")
        if errors:
            raise PositionRiskValidationError(
                "Position failed factory validation",
                errors=tuple(errors),
            )
