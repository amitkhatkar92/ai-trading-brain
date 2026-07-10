"""iios/investment/market/structure/confidence_calculator.py
Calculate confidence scores for each structure element.
Pure structural factors — no indicators.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.structure.models import (
    Bar,
    BreakoutEvent,
    SwingPoint,
    TrendState,
    Zone,
)

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """Compute 0-100 confidence scores for structural elements."""

    def swing_confidence(
        self,
        swing: SwingPoint,
        bars: List[Bar],
    ) -> float:
        """0-100. More confirmation bars + higher volume = higher confidence."""
        score = 0.0

        # Left and right bars (0-40 points total)
        left_score = min(swing.left_bars / 5.0, 1.0) * 20.0
        right_score = min(swing.right_bars / 5.0, 1.0) * 20.0
        score += left_score + right_score

        # Volume vs average (0-30 points)
        if bars and swing.volume > 0:
            avg_vol = sum(b.volume for b in bars) / len(bars)
            if avg_vol > 0:
                vol_ratio = swing.volume / avg_vol
                vol_score = min(vol_ratio / 2.0, 1.0) * 30.0
                score += vol_score

        # Price displacement (bar_range vs avg_range) (0-30 points)
        if bars:
            avg_range = sum(b.range for b in bars) / len(bars)
            if avg_range > 0:
                range_ratio = swing.bar_range / avg_range
                range_score = min(range_ratio / 2.0, 1.0) * 30.0
                score += range_score

        return max(0.0, min(100.0, score))

    def trend_confidence(self, state: TrendState) -> float:
        """0-100. More legs + shallower corrections = higher confidence."""
        score = 0.0

        # Leg count (0-40 points): 4+ legs = full marks
        leg_score = min(state.leg_count / 4.0, 1.0) * 40.0
        score += leg_score

        # Correction depth (0-40 points): shallow corrections = strong trend
        # depth 0.3 = perfect, depth 0.7+ = weak
        corr_depth = max(0.0, min(state.correction_depth, 1.0))
        shallow_score = (1.0 - corr_depth) * 40.0
        score += shallow_score

        # Confirmed bonus (0-20 points)
        if state.confirmed:
            score += 20.0

        return max(0.0, min(100.0, score))

    def zone_confidence(
        self,
        zone: Zone,
        current_price: float,
    ) -> float:
        """0-100. More touches, longer age, tighter zone = higher confidence."""
        score = 0.0

        # Touch count (0-40 points)
        touch_score = min(zone.touch_count / 5.0, 1.0) * 40.0
        score += touch_score

        # Zone age (0-20 points)
        age = zone.last_touch_index - zone.first_touch_index
        age_score = min(age / 100.0, 1.0) * 20.0
        score += age_score

        # Zone tightness: narrow width relative to price (0-20 points)
        if current_price > 0 and zone.width > 0:
            width_pct = zone.width / current_price
            tightness_score = max(0.0, 1.0 - width_pct / 0.05) * 20.0
            score += tightness_score

        # Retested and held bonus (0-20 points)
        if zone.retested_after_break:
            score += 20.0
        elif zone.touch_count >= 3:
            score += 10.0

        return max(0.0, min(100.0, score))

    def breakout_confidence(self, event: BreakoutEvent) -> float:
        """0-100. Further close beyond zone + volume confirmation."""
        score = 0.0

        # Close distance beyond zone (0-50 points)
        ref_price = event.zone.mid if event.zone.mid > 0 else 1.0
        pct_beyond = event.close_beyond / ref_price if ref_price > 0 else 0.0
        beyond_score = min(pct_beyond / 0.02, 1.0) * 50.0  # 2% beyond = full marks
        score += beyond_score

        # Volume confirmation (0-50 points)
        if event.avg_volume_20 > 0:
            vol_ratio = event.trigger_volume / event.avg_volume_20
            vol_score = min(vol_ratio / 2.0, 1.0) * 50.0
            score += vol_score

        return max(0.0, min(100.0, score))

    def data_quality(self, bars: List[Bar]) -> float:
        """0-100. Check for gaps, zero volumes, zero ranges."""
        if not bars:
            return 0.0

        total = len(bars)
        issues = 0

        for bar in bars:
            if bar.volume == 0:
                issues += 1
            if bar.range == 0:
                issues += 1
            if bar.high < bar.low:
                issues += 2
            if bar.close <= 0 or bar.open <= 0:
                issues += 2

        issue_rate = issues / (total * 2.0)  # normalise
        score = (1.0 - min(issue_rate, 1.0)) * 100.0
        return max(0.0, min(100.0, score))
