"""iios/investment/market/regime/regime_constraints.py
Hard trading constraints per market regime.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from iios.investment.market.regime.models import RegimeType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegimeConstraint:
    """Hard trading constraints for a specific market regime."""

    regime:                    RegimeType
    max_positions:             Optional[int]   # None = no limit
    max_position_size_pct:     float           # fraction of normal size
    require_trend_confirmation: bool
    min_structure_quality:     float           # 0-100
    forbidden_directions:      List[str]       = field(default_factory=list)
    notes:                     str             = ""


REGIME_CONSTRAINTS: Dict[RegimeType, RegimeConstraint] = {
    RegimeType.BULL: RegimeConstraint(
        regime=RegimeType.BULL,
        max_positions=None,
        max_position_size_pct=1.0,
        require_trend_confirmation=True,
        min_structure_quality=50.0,
        forbidden_directions=[],
    ),
    RegimeType.BEAR: RegimeConstraint(
        regime=RegimeType.BEAR,
        max_positions=5,
        max_position_size_pct=0.5,
        require_trend_confirmation=True,
        min_structure_quality=50.0,
        forbidden_directions=["long"],
        notes="Only short or hedging positions allowed",
    ),
    RegimeType.SIDEWAYS: RegimeConstraint(
        regime=RegimeType.SIDEWAYS,
        max_positions=10,
        max_position_size_pct=0.75,
        require_trend_confirmation=False,
        min_structure_quality=40.0,
        forbidden_directions=[],
    ),
    RegimeType.TRENDING: RegimeConstraint(
        regime=RegimeType.TRENDING,
        max_positions=None,
        max_position_size_pct=1.0,
        require_trend_confirmation=True,
        min_structure_quality=55.0,
        forbidden_directions=[],
    ),
    RegimeType.RANGING: RegimeConstraint(
        regime=RegimeType.RANGING,
        max_positions=10,
        max_position_size_pct=0.75,
        require_trend_confirmation=False,
        min_structure_quality=35.0,
        forbidden_directions=[],
    ),
    RegimeType.EXPANSION: RegimeConstraint(
        regime=RegimeType.EXPANSION,
        max_positions=None,
        max_position_size_pct=1.0,
        require_trend_confirmation=False,
        min_structure_quality=45.0,
        forbidden_directions=[],
    ),
    RegimeType.CONTRACTION: RegimeConstraint(
        regime=RegimeType.CONTRACTION,
        max_positions=5,
        max_position_size_pct=0.5,
        require_trend_confirmation=False,
        min_structure_quality=35.0,
        forbidden_directions=[],
    ),
    RegimeType.RECOVERY: RegimeConstraint(
        regime=RegimeType.RECOVERY,
        max_positions=8,
        max_position_size_pct=0.75,
        require_trend_confirmation=False,
        min_structure_quality=40.0,
        forbidden_directions=[],
    ),
    RegimeType.DISTRIBUTION: RegimeConstraint(
        regime=RegimeType.DISTRIBUTION,
        max_positions=3,
        max_position_size_pct=0.5,
        require_trend_confirmation=True,
        min_structure_quality=50.0,
        forbidden_directions=["long"],
        notes="No long positions in distribution",
    ),
    RegimeType.ACCUMULATION: RegimeConstraint(
        regime=RegimeType.ACCUMULATION,
        max_positions=8,
        max_position_size_pct=0.75,
        require_trend_confirmation=False,
        min_structure_quality=40.0,
        forbidden_directions=[],
    ),
    RegimeType.VOLATILE: RegimeConstraint(
        regime=RegimeType.VOLATILE,
        max_positions=3,
        max_position_size_pct=0.5,
        require_trend_confirmation=False,
        min_structure_quality=30.0,
        forbidden_directions=[],
    ),
    RegimeType.CALM: RegimeConstraint(
        regime=RegimeType.CALM,
        max_positions=None,
        max_position_size_pct=1.0,
        require_trend_confirmation=False,
        min_structure_quality=45.0,
        forbidden_directions=[],
    ),
    RegimeType.TRANSITION: RegimeConstraint(
        regime=RegimeType.TRANSITION,
        max_positions=2,
        max_position_size_pct=0.25,
        require_trend_confirmation=True,
        min_structure_quality=55.0,
        forbidden_directions=[],
        notes="Minimal exposure during regime transition",
    ),
    RegimeType.CRISIS: RegimeConstraint(
        regime=RegimeType.CRISIS,
        max_positions=0,
        max_position_size_pct=0.0,
        require_trend_confirmation=True,
        min_structure_quality=60.0,
        forbidden_directions=["long", "short"],
        notes="No new positions during crisis",
    ),
    RegimeType.UNKNOWN: RegimeConstraint(
        regime=RegimeType.UNKNOWN,
        max_positions=0,
        max_position_size_pct=0.0,
        require_trend_confirmation=True,
        min_structure_quality=60.0,
        forbidden_directions=["long", "short"],
        notes="No trading in unknown regime",
    ),
}


class RegimeConstraintEngine:
    """Provides and enforces regime-based trading constraints."""

    def get(self, regime: RegimeType) -> RegimeConstraint:
        """Return constraints for a regime. Falls back to UNKNOWN."""
        return REGIME_CONSTRAINTS.get(regime, REGIME_CONSTRAINTS[RegimeType.UNKNOWN])

    def check(
        self,
        strategy_type: str,
        regime: RegimeType,
        direction: str,
        structure_quality: float,
        trend_confirmed: bool,
    ) -> Tuple[bool, str]:
        """
        Returns (allowed, reason_string).
        Checks: max_positions limit, forbidden directions, min_quality, trend_confirmation.
        """
        constraint = self.get(regime)

        # max_positions == 0 → nothing allowed
        if constraint.max_positions == 0:
            return False, f"No positions allowed in {regime.value} regime"

        # Forbidden direction
        if direction in constraint.forbidden_directions:
            return (
                False,
                f"{direction} trades forbidden in {regime.value} regime",
            )

        # Minimum structure quality
        if structure_quality < constraint.min_structure_quality:
            return (
                False,
                f"Structure quality {structure_quality:.1f} below minimum "
                f"{constraint.min_structure_quality:.1f} for {regime.value}",
            )

        # Trend confirmation requirement
        if constraint.require_trend_confirmation and not trend_confirmed:
            return (
                False,
                f"Trend confirmation required in {regime.value} regime",
            )

        return True, "Constraint check passed"
