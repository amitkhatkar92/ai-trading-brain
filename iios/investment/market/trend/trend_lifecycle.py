"""iios/investment/market/trend/trend_lifecycle.py
Determines TrendStage from structure + legs + momentum.
"""
from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

from iios.investment.market.trend.models import (
    TrendStage,
    TrendEventType,
    TrendMomentumState,
    TrendLegMetrics,
    ImpulseQuality,
    CorrectionQuality,
)

if TYPE_CHECKING:
    from iios.investment.market.structure.models import TrendState


class TrendLifecycleDetector:
    """
    Determines TrendStage from structure + legs + momentum.
    Pure computation — no state.
    """

    def detect(
        self,
        trend_state: "TrendState",
        legs: List[TrendLegMetrics],
        momentum: TrendMomentumState,
        prev_stage: TrendStage = TrendStage.EMERGING,
    ) -> Tuple[TrendStage, float]:
        """
        Returns (stage, stage_confidence).
        Rules checked in priority order.
        """
        phase = trend_state.phase.value
        leg_count = trend_state.leg_count
        confirmed = trend_state.confirmed
        correction_depth = trend_state.correction_depth

        impulse_legs = [l for l in legs if l.is_impulse]
        latest_impulse_q = (
            impulse_legs[-1].impulse_quality if impulse_legs else ImpulseQuality.MODERATE
        )
        correction_legs = [l for l in legs if not l.is_impulse]
        latest_correction_q = (
            correction_legs[-1].correction_quality if correction_legs else CorrectionQuality.NORMAL
        )

        # -- Priority ordered rules --

        # COMPLETED
        if (
            prev_stage in (TrendStage.REVERSING, TrendStage.FAILING)
            and confirmed
            and leg_count >= 1
        ):
            stage = TrendStage.COMPLETED
            raw_conf = 0.90

        # REVERSING
        elif phase == "reversal":
            stage = TrendStage.REVERSING
            raw_conf = 0.85

        # FAILING
        elif (
            (phase == "exhaustion" and latest_impulse_q == ImpulseQuality.WEAK)
            or correction_depth > 0.85
        ):
            stage = TrendStage.FAILING
            raw_conf = 0.75

        # EXHAUSTING
        elif (
            (momentum.is_decelerating and correction_depth > 0.618)
            or phase == "exhaustion"
            or (
                leg_count >= 5
                and latest_impulse_q == ImpulseQuality.WEAK
                and latest_correction_q == CorrectionQuality.DEEP
            )
        ):
            stage = TrendStage.EXHAUSTING
            raw_conf = 0.70

        # MATURE
        elif (
            leg_count >= 5
            and confirmed
            and phase not in ("reversal", "exhaustion")
            and correction_depth <= 0.618
        ):
            stage = TrendStage.MATURE
            raw_conf = 0.72

        # ESTABLISHED
        elif (
            leg_count >= 3
            and confirmed
            and phase not in ("reversal", "exhaustion")
            and correction_depth <= 0.618
        ):
            stage = TrendStage.ESTABLISHED
            raw_conf = 0.80

        # DEVELOPING
        elif leg_count >= 2 and confirmed:
            stage = TrendStage.DEVELOPING
            raw_conf = 0.70

        # EMERGING (fallback)
        else:
            stage = TrendStage.EMERGING
            raw_conf = 0.55

        # Scale by structure quality — use correction_depth as rough proxy
        # actual quality comes from StructureQualityScore but we don't have it here
        confidence = raw_conf  # caller adjusts if needed

        return (stage, confidence)

    def detect_event(
        self,
        prev_stage: TrendStage,
        new_stage: TrendStage,
        trend_state: "TrendState",
    ) -> Optional[TrendEventType]:
        """Determine which TrendEventType occurred given a stage transition."""
        if prev_stage == TrendStage.EMERGING and new_stage == TrendStage.DEVELOPING:
            return TrendEventType.TREND_START

        if prev_stage == TrendStage.DEVELOPING and new_stage == TrendStage.ESTABLISHED:
            return TrendEventType.TREND_CONTINUATION

        if prev_stage == TrendStage.ESTABLISHED and new_stage == TrendStage.MATURE:
            return TrendEventType.TREND_CONTINUATION

        if prev_stage == TrendStage.MATURE and new_stage == TrendStage.EXHAUSTING:
            return TrendEventType.TREND_SLOWDOWN

        if prev_stage == TrendStage.EXHAUSTING and new_stage == TrendStage.FAILING:
            return TrendEventType.TREND_WEAKENING

        if prev_stage == TrendStage.FAILING and new_stage == TrendStage.REVERSING:
            return TrendEventType.TREND_FAILURE

        if prev_stage == TrendStage.REVERSING and new_stage == TrendStage.COMPLETED:
            return TrendEventType.TREND_EXHAUSTION

        if new_stage == TrendStage.EMERGING and prev_stage == TrendStage.COMPLETED:
            return TrendEventType.TREND_RESTART

        if (
            prev_stage in (TrendStage.EXHAUSTING, TrendStage.FAILING)
            and new_stage == TrendStage.ESTABLISHED
        ):
            return TrendEventType.TREND_RECOVERY

        return None
