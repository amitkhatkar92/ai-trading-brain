"""iios/investment/market/structure/structure_quality.py
Facade for market structure quality assessment.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.structure.confidence_calculator import ConfidenceCalculator
from iios.investment.market.structure.models import (
    Bar,
    BreakoutEvent,
    StructureQualityScore,
    SwingSequence,
    TrendState,
    Zone,
)
from iios.investment.market.structure.structure_score import StructureScorer

logger = logging.getLogger(__name__)


class StructureQualityAssessor:
    """Facade: compute a single StructureQualityScore for the current state."""

    def __init__(
        self,
        calculator: ConfidenceCalculator,
        scorer: StructureScorer,
    ) -> None:
        self._calc = calculator
        self._scorer = scorer

    def assess(
        self,
        bars: List[Bar],
        trend: TrendState,
        sequence: SwingSequence,
        zones: List[Zone],
        breakout: Optional[BreakoutEvent],
    ) -> StructureQualityScore:
        # Swing confidence: average of all recent swings (up to 5)
        all_swings = (sequence.highs + sequence.lows)[:5]
        if all_swings:
            swing_conf = sum(
                self._calc.swing_confidence(sw, bars) for sw in all_swings
            ) / len(all_swings)
        else:
            swing_conf = 0.0

        trend_conf = self._calc.trend_confidence(trend)

        # Zone confidence: average of up to 3 active zones
        current_price = bars[-1].close if bars else 0.0
        if zones:
            zone_sample = zones[:3]
            zone_conf = sum(
                self._calc.zone_confidence(z, current_price) for z in zone_sample
            ) / len(zone_sample)
        else:
            zone_conf = 0.0

        breakout_conf = self._calc.breakout_confidence(breakout) if breakout else 0.0
        data_qual = self._calc.data_quality(bars)
        valid_swings = len(sequence.highs) + len(sequence.lows)

        return self._scorer.score(
            swing_conf=swing_conf,
            trend_conf=trend_conf,
            zone_conf=zone_conf,
            breakout_conf=breakout_conf,
            data_quality=data_qual,
            bar_count=len(bars),
            valid_swing_count=valid_swings,
        )
