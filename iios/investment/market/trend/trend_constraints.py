"""iios/investment/market/trend/trend_constraints.py
Trend stage constraints for strategy entry validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from iios.investment.market.trend.models import TrendStage


@dataclass(frozen=True)
class TrendConstraint:
    stage: TrendStage
    min_confidence: float
    min_quality: float
    forbidden_directions: List[str]
    require_confirmation: bool
    max_position_size_pct: float
    notes: str = ""


TREND_CONSTRAINTS: Dict[TrendStage, TrendConstraint] = {
    TrendStage.EMERGING: TrendConstraint(
        stage=TrendStage.EMERGING,
        min_confidence=0.40,
        min_quality=30.0,
        forbidden_directions=[],
        require_confirmation=False,
        max_position_size_pct=0.50,
        notes="Early stage; reduce size, no confirmation required",
    ),
    TrendStage.DEVELOPING: TrendConstraint(
        stage=TrendStage.DEVELOPING,
        min_confidence=0.50,
        min_quality=40.0,
        forbidden_directions=[],
        require_confirmation=True,
        max_position_size_pct=0.75,
        notes="Developing trend; confirmation required",
    ),
    TrendStage.ESTABLISHED: TrendConstraint(
        stage=TrendStage.ESTABLISHED,
        min_confidence=0.55,
        min_quality=50.0,
        forbidden_directions=[],
        require_confirmation=True,
        max_position_size_pct=1.00,
        notes="Established trend; full size allowed",
    ),
    TrendStage.MATURE: TrendConstraint(
        stage=TrendStage.MATURE,
        min_confidence=0.50,
        min_quality=45.0,
        forbidden_directions=[],
        require_confirmation=True,
        max_position_size_pct=0.75,
        notes="Mature trend; corrections may deepen",
    ),
    TrendStage.EXHAUSTING: TrendConstraint(
        stage=TrendStage.EXHAUSTING,
        min_confidence=0.55,
        min_quality=50.0,
        forbidden_directions=["momentum", "breakout"],
        require_confirmation=True,
        max_position_size_pct=0.50,
        notes="Exhausting trend; momentum/breakout forbidden",
    ),
    TrendStage.FAILING: TrendConstraint(
        stage=TrendStage.FAILING,
        min_confidence=0.60,
        min_quality=55.0,
        forbidden_directions=["momentum", "breakout", "swing", "position"],
        require_confirmation=True,
        max_position_size_pct=0.25,
        notes="Failing trend; most strategies forbidden",
    ),
    TrendStage.REVERSING: TrendConstraint(
        stage=TrendStage.REVERSING,
        min_confidence=0.65,
        min_quality=55.0,
        forbidden_directions=["momentum", "breakout", "swing", "position", "retest"],
        require_confirmation=True,
        max_position_size_pct=0.10,
        notes="Reversing; only mean_reversion allowed",
    ),
    TrendStage.COMPLETED: TrendConstraint(
        stage=TrendStage.COMPLETED,
        min_confidence=1.0,
        min_quality=100.0,
        forbidden_directions=["momentum", "breakout", "retest", "mean_reversion", "swing", "position"],
        require_confirmation=True,
        max_position_size_pct=0.00,
        notes="Completed trend; all strategies forbidden",
    ),
}


class TrendConstraintEngine:
    def get(self, stage: TrendStage) -> TrendConstraint:
        return TREND_CONSTRAINTS.get(
            stage,
            TREND_CONSTRAINTS[TrendStage.EMERGING],
        )

    def check(
        self,
        strategy_type: str,
        stage: TrendStage,
        direction: str,
        confidence: float,
        quality_overall: float,
        trend_confirmed: bool,
    ) -> Tuple[bool, str]:
        """Returns (allowed, reason). Checks all constraints."""
        constraint = self.get(stage)

        if constraint.max_position_size_pct == 0.0:
            return (False, f"Stage {stage.value}: all trading blocked")

        if strategy_type in constraint.forbidden_directions:
            return (False, f"Stage {stage.value}: {strategy_type} is forbidden")

        if confidence < constraint.min_confidence:
            return (
                False,
                f"Confidence {confidence:.2f} < required {constraint.min_confidence:.2f}",
            )

        if quality_overall < constraint.min_quality:
            return (
                False,
                f"Quality {quality_overall:.1f} < required {constraint.min_quality:.1f}",
            )

        if constraint.require_confirmation and not trend_confirmed:
            return (False, "Trend confirmation required but not confirmed")

        return (True, f"Stage {stage.value}: {strategy_type} allowed")
